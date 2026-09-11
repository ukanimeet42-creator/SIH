"""
VoxGuard Engine — Security Utilities

JWT session token creation, validation, and WebSocket auth helpers.
"""

from __future__ import annotations

import hashlib
import time
from typing import Optional

from fastapi import HTTPException, WebSocket, status
from jose import JWTError, jwt

from app.core.config import get_settings

_settings = get_settings()


def create_session_token(session_id: str, extra_claims: Optional[dict] = None) -> str:
    """Create a signed JWT for a WebSocket session.

    Args:
        session_id: Unique session identifier.
        extra_claims: Additional JWT payload fields.

    Returns:
        Encoded JWT string.
    """
    payload = {
        "sub": session_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + _settings.JWT_EXPIRY_MINUTES * 60,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _settings.JWT_SECRET, algorithm=_settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT session token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            _settings.JWT_SECRET,
            algorithms=[_settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session token: {exc}",
        )


async def authenticate_websocket(websocket: WebSocket) -> dict:
    """Authenticate a WebSocket connection using a query-param or header token.

    Tries `?token=...` first, then the `Authorization: Bearer ...` header.
    In development mode (DEBUG=True) with no token provided, returns a
    placeholder payload so testing is seamless.

    Args:
        websocket: The incoming WebSocket connection.

    Returns:
        Decoded JWT payload dict.
    """
    # Try query param
    token = websocket.query_params.get("token")

    # Fall back to Authorization header
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    # Dev-mode bypass
    if not token:
        if _settings.DEBUG:
            return {"sub": "dev-session", "mode": "debug"}
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    return verify_token(token)


def hash_pii(value: str) -> str:
    """SHA-256 hash a PII value for zero-knowledge storage.

    Args:
        value: Raw PII string (phone number, session ID, etc.).

    Returns:
        Hex-encoded SHA-256 digest.
    """
    if not _settings.ENABLE_PII_MASKING:
        return value
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
