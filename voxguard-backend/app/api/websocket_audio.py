"""
VoxGuard Engine — Live Audio WebSocket Endpoint

Bi-directional WebSocket at ``/ws/live-stream/{session_id}``:

- **Client → Server**: Continuous binary PCM Int16 audio chunks (16 kHz mono).
- **Server → Client**: JSON detection results streamed back in real time,
  plus Voice CAPTCHA challenge triggers when confidence exceeds threshold.

Privacy: Raw audio is processed in RAM only and never persisted to disk
(Zero-Retention Policy).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import authenticate_websocket, hash_pii
from app.models.schemas import (
    DetectionVerdict,
    IncidentRecord,
    SessionInfo,
    StreamMessage,
)
from app.services.audio_preprocessor import SlidingWindowBuffer, pcm_int16_to_float32, validate_audio
from app.services.detector_engine import DetectorEngine
from app.services.prevention_service import generate_challenge_phrase

logger = logging.getLogger(__name__)
_settings = get_settings()

router = APIRouter()

# ── In-Memory Session Registry ───────────────────────────────────────
# Maps session_id → SessionInfo for active connections.

active_sessions: Dict[str, SessionInfo] = {}
incident_log: list[IncidentRecord] = []

# Global stats
_start_time = time.time()
_total_chunks = 0
_total_threats = 0
_latency_sum = 0.0
_latency_count = 0


def get_active_sessions() -> Dict[str, SessionInfo]:
    """Return the active sessions dict (used by telemetry routes)."""
    return active_sessions


def get_incident_log() -> list[IncidentRecord]:
    """Return the incident log (used by telemetry routes)."""
    return incident_log


def get_global_stats() -> dict:
    """Return global stats for telemetry."""
    return {
        "start_time": _start_time,
        "total_chunks": _total_chunks,
        "total_threats": _total_threats,
        "avg_latency_ms": _latency_sum / _latency_count if _latency_count > 0 else 0.0,
    }


@router.websocket("/ws/live-stream/{session_id}")
async def live_stream(websocket: WebSocket, session_id: str) -> None:
    """Live audio analysis WebSocket endpoint.

    Protocol:
        1. Client connects with optional ``?token=JWT`` query param.
        2. Client sends binary PCM Int16 chunks (16 kHz mono).
        3. Server responds with JSON :class:`StreamMessage` for each
           analysed window.
        4. If synthetic confidence exceeds threshold, server includes a
           ``challenge`` field with a Voice CAPTCHA phrase.
        5. Client can send a JSON message with ``{"type": "challenge_response",
           "transcript": "..."}`` to verify the challenge via Web Speech API.

    Args:
        websocket: The WebSocket connection.
        session_id: Unique session identifier from URL path.
    """
    global _total_chunks, _total_threats, _latency_sum, _latency_count

    # ── Auth ─────────────────────────────────────────────────────────
    await websocket.accept()
    try:
        auth_payload = await authenticate_websocket(websocket)
    except Exception as e:
        await websocket.send_json({"type": "error", "error": f"Authentication failed: {e}"})
        await websocket.close(code=1008)
        return

    # ── Session Setup ────────────────────────────────────────────────
    masked_id = hash_pii(session_id)
    session = SessionInfo(session_id=session_id, masked_session_id=masked_id[:16])
    active_sessions[session_id] = session

    buffer = SlidingWindowBuffer()
    engine = DetectorEngine()
    await engine.initialise()

    pending_challenge: str | None = None
    consecutive_synthetic = 0

    logger.info("WebSocket connected — session=%s (masked=%s)", session_id, masked_id[:16])

    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "config": {
                "sample_rate": _settings.SAMPLE_RATE,
                "chunk_duration_s": _settings.CHUNK_DURATION_S,
                "detection_threshold": _settings.DETECTION_THRESHOLD,
            },
        })

        while True:
            message = await websocket.receive()

            # ── Handle text messages (challenge responses, control) ───
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type", "")

                    if msg_type == "challenge_response":
                        # Frontend Web Speech API path
                        transcript = data.get("transcript", "")
                        if pending_challenge and transcript:
                            from app.services.prevention_service import verify_challenge_response
                            result = await verify_challenge_response(
                                target_phrase=pending_challenge,
                                recognised_text=transcript,
                            )
                            await websocket.send_json({
                                "type": "challenge_result",
                                "session_id": session_id,
                                "matched": result.matched,
                                "similarity_score": result.similarity_score,
                                "expected_phrase": result.expected_phrase,
                                "recognised_text": result.recognised_text,
                            })
                            if result.matched:
                                pending_challenge = None
                                consecutive_synthetic = 0
                                logger.info("Challenge passed — session=%s", session_id)
                            else:
                                logger.warning("Challenge failed — session=%s", session_id)

                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": time.time()})

                except json.JSONDecodeError:
                    pass
                continue

            # ── Handle binary audio data ─────────────────────────────
            if "bytes" not in message:
                continue

            raw_bytes = message["bytes"]
            if not raw_bytes:
                continue

            try:
                audio = pcm_int16_to_float32(raw_bytes)
                audio = validate_audio(audio)
            except (ValueError, Exception) as e:
                logger.warning("Audio preprocessing error: %s", e)
                continue

            # Feed into sliding window buffer
            windows = buffer.add_audio(audio)

            for window in windows:
                # Run detection
                result = engine.predict_chunk(window)

                session.chunks_processed += 1
                _total_chunks += 1
                _latency_sum += result.latency_ms
                _latency_count += 1
                session.avg_latency_ms = (
                    (session.avg_latency_ms * (session.chunks_processed - 1) + result.latency_ms)
                    / session.chunks_processed
                )

                # Build response message
                msg = StreamMessage(
                    type="detection_result",
                    session_id=session_id,
                    result=result,
                )

                # ── Prevention logic ─────────────────────────────────
                if result.verdict == DetectionVerdict.SYNTHETIC:
                    consecutive_synthetic += 1
                    session.threats_detected += 1
                    _total_threats += 1

                    # Log incident
                    incident = IncidentRecord(
                        session_id=session_id,
                        masked_session_id=masked_id[:16],
                        detection=result,
                        action_taken="challenge_issued" if consecutive_synthetic >= 2 else "flagged",
                    )
                    incident_log.append(incident)

                    # Issue challenge after 2 consecutive synthetic detections
                    if consecutive_synthetic >= 2 and pending_challenge is None:
                        pending_challenge = generate_challenge_phrase()
                        msg.challenge = pending_challenge
                        logger.warning(
                            "Voice CAPTCHA triggered — session=%s, confidence=%.3f",
                            session_id, result.confidence,
                        )
                else:
                    consecutive_synthetic = max(0, consecutive_synthetic - 1)

                await websocket.send_json(msg.model_dump(mode="json"))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected — session=%s", session_id)
    except Exception:
        logger.exception("WebSocket error — session=%s", session_id)
    finally:
        session.is_active = False
        active_sessions.pop(session_id, None)
        buffer.reset()
        logger.info(
            "Session cleanup — session=%s, chunks=%d, threats=%d",
            session_id, session.chunks_processed, session.threats_detected,
        )
