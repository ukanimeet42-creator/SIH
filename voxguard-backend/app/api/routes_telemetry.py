"""
VoxGuard Engine — REST Telemetry Endpoints

Provides read-only access to session metadata, incident history, and
aggregate detection statistics for the dashboard frontend.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Query

from app.api.websocket_audio import get_active_sessions, get_global_stats, get_incident_log
from app.core.config import get_settings
from app.models.schemas import (
    IncidentRecord,
    SessionInfo,
    TelemetryPayload,
    TelemetryStats,
)
from app.services.prevention_service import generate_challenge_phrase

_settings = get_settings()
router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/stats", response_model=TelemetryPayload)
async def get_stats() -> TelemetryPayload:
    """Return aggregate detection statistics."""
    sessions = get_active_sessions()
    global_stats = get_global_stats()
    incidents = get_incident_log()

    stats = TelemetryStats(
        total_sessions=len(sessions) + len([i for i in incidents]),
        active_sessions=len(sessions),
        total_chunks_analysed=global_stats["total_chunks"],
        threats_blocked=global_stats["total_threats"],
        avg_latency_ms=round(global_stats["avg_latency_ms"], 2),
        uptime_seconds=round(time.time() - global_stats["start_time"], 2),
    )
    return TelemetryPayload(stats=stats)


@router.get("/sessions", response_model=TelemetryPayload)
async def get_sessions() -> TelemetryPayload:
    """Return list of active analysis sessions."""
    sessions = list(get_active_sessions().values())
    return TelemetryPayload(sessions=sessions)


@router.get("/incidents", response_model=TelemetryPayload)
async def get_incidents(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> TelemetryPayload:
    """Return paginated incident history (most recent first)."""
    all_incidents = get_incident_log()
    # Reverse for most-recent-first
    recent = list(reversed(all_incidents))[offset: offset + limit]
    return TelemetryPayload(incidents=recent)


@router.get("/challenge", response_model=dict)
async def get_challenge_phrase() -> dict:
    """Generate a new Voice CAPTCHA challenge phrase (for testing)."""
    phrase = generate_challenge_phrase()
    return {"challenge_phrase": phrase}


@router.post("/verify-challenge", response_model=dict)
async def verify_challenge(
    target_phrase: str,
    recognised_text: str,
) -> dict:
    """Verify a spoken challenge response (text-only path for frontend STT)."""
    from app.services.prevention_service import verify_challenge_response

    result = await verify_challenge_response(
        target_phrase=target_phrase,
        recognised_text=recognised_text,
    )
    return result.model_dump(mode="json")
