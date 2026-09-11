"""
VoxGuard Engine — Pydantic V2 Schemas

Strict payload contracts for API requests, responses, WebSocket messages,
and internal data transfer objects.  Includes SHA-256 PII masking via
validator hooks when ENABLE_PII_MASKING is active.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings

_settings = get_settings()


# ── Enums ────────────────────────────────────────────────────────────

class DetectionVerdict(str, Enum):
    """Possible detection outcomes."""
    HUMAN = "human"
    SYNTHETIC = "synthetic"
    UNCERTAIN = "uncertain"


class AnomalyFlag(str, Enum):
    """Acoustic anomaly indicators."""
    SPECTRAL_FLATNESS = "spectral_flatness_abnormal"
    HF_ROLLOFF = "high_freq_rolloff_anomaly"
    PHASE_DISCONTINUITY = "vocoder_phase_discontinuity"
    ZCR_ANOMALY = "zero_crossing_rate_anomaly"
    MEL_ENERGY_FLAT = "mel_energy_distribution_flat"
    LOW_DYNAMIC_RANGE = "low_dynamic_range"


# ── Detection ────────────────────────────────────────────────────────

class DetectionResult(BaseModel):
    """Result returned for every analysed audio chunk."""
    is_synthetic: bool = Field(..., description="True if the audio chunk is classified as synthetic / cloned.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Probability that the audio is synthetic (0 = human, 1 = synthetic).")
    verdict: DetectionVerdict = Field(..., description="Categorical verdict.")
    anomaly_flags: List[AnomalyFlag] = Field(default_factory=list, description="List of triggered acoustic anomalies.")
    latency_ms: float = Field(..., ge=0.0, description="Inference latency in milliseconds.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    spectral_flatness: Optional[float] = Field(None, description="Measured spectral flatness (Wiener entropy).")
    spectral_centroid_hz: Optional[float] = Field(None, description="Spectral centroid in Hz.")
    hf_energy_ratio: Optional[float] = Field(None, description="Ratio of energy above 8 kHz to total energy.")


class StreamMessage(BaseModel):
    """WebSocket message from server → client."""
    type: str = Field("detection_result", description="Message type discriminator.")
    session_id: str
    result: Optional[DetectionResult] = None
    challenge: Optional[str] = None  # Non-null when a voice CAPTCHA is triggered
    error: Optional[str] = None


# ── Voice CAPTCHA / Prevention ───────────────────────────────────────

class ChallengeRequest(BaseModel):
    """Request to generate a new voice CAPTCHA challenge."""
    session_id: str
    reason: str = "synthetic_detected"


class ChallengeResponse(BaseModel):
    """Result of verifying a spoken challenge response."""
    matched: bool = Field(..., description="Whether the spoken transcript matches the challenge phrase.")
    expected_phrase: str
    recognised_text: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    verified_at: datetime = Field(default_factory=datetime.utcnow)


# ── Telemetry & Incidents ────────────────────────────────────────────

class SessionInfo(BaseModel):
    """Metadata for an active analysis session."""
    session_id: str
    masked_session_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    chunks_processed: int = 0
    threats_detected: int = 0
    avg_latency_ms: float = 0.0

    @field_validator("masked_session_id", mode="before")
    @classmethod
    def _mask_session(cls, v, info):
        """Auto-fill masked_session_id from session_id when PII masking is on."""
        if v is None and _settings.ENABLE_PII_MASKING:
            raw = info.data.get("session_id", "")
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        return v


class IncidentRecord(BaseModel):
    """A logged synthetic-voice detection incident."""
    id: Optional[str] = None
    session_id: str
    masked_session_id: Optional[str] = None
    detection: DetectionResult
    action_taken: str = Field("challenge_issued", description="What prevention action was triggered.")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("masked_session_id", mode="before")
    @classmethod
    def _mask_session(cls, v, info):
        if v is None and _settings.ENABLE_PII_MASKING:
            raw = info.data.get("session_id", "")
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        return v


class TelemetryStats(BaseModel):
    """Aggregate statistics for the telemetry dashboard."""
    total_sessions: int = 0
    active_sessions: int = 0
    total_chunks_analysed: int = 0
    threats_blocked: int = 0
    avg_latency_ms: float = 0.0
    detection_accuracy: Optional[float] = None  # Only set when ground-truth labels exist
    uptime_seconds: float = 0.0


class TelemetryPayload(BaseModel):
    """Wrapper for telemetry REST responses."""
    stats: Optional[TelemetryStats] = None
    sessions: Optional[List[SessionInfo]] = None
    incidents: Optional[List[IncidentRecord]] = None
