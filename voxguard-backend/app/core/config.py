"""
VoxGuard Engine — Application Configuration

Loads all hyperparameters, API keys, and model paths from environment
variables with sensible defaults for development.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for VoxGuard Engine.

    All values can be overridden via a `.env` file or exported environment
    variables. Defaults are tuned for local CPU-only development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "VoxGuard Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Audio Pipeline ───────────────────────────────────────────────
    SAMPLE_RATE: int = 16_000          # Target sample rate (16 kHz mono)
    CHUNK_DURATION_S: float = 1.5      # Sliding window length in seconds
    HOP_DURATION_S: float = 0.5        # Hop / stride in seconds
    AUDIO_CHANNELS: int = 1            # Mono
    AUDIO_DTYPE: str = "int16"         # PCM Int16 from frontend AudioWorklet

    # ── Detector ─────────────────────────────────────────────────────
    DETECTION_THRESHOLD: float = 0.10  # DEMO HACK: Hyper-sensitive to catch phone speakers
    MODEL_PATH: Optional[str] = "models/aasist.onnx" # Default AASIST ONNX model path
    USE_ONNX: bool = True              # Enable ONNX model fusion by default
    MAX_INFERENCE_MS: int = 200        # Hard latency cap

    # ── DSP Heuristic Thresholds ─────────────────────────────────────
    SPECTRAL_FLATNESS_THRESHOLD: float = 0.35   # Above → suspiciously flat
    HF_ROLLOFF_THRESHOLD: float = 0.70          # Rolloff ratio above 8 kHz
    ZCR_LOW_THRESHOLD: float = 0.02             # Abnormally low ZCR
    ZCR_HIGH_THRESHOLD: float = 0.20            # Abnormally high ZCR
    MEL_ENERGY_VARIANCE_THRESHOLD: float = 0.15 # Low variance → vocoder

    # ── Prevention / Voice CAPTCHA ───────────────────────────────────
    CHALLENGE_TIMEOUT_S: int = 15      # Max seconds to respond to challenge
    USE_BACKEND_STT: bool = True       # True → faster-whisper, False → rely on frontend Web Speech API
    WHISPER_MODEL_SIZE: str = "tiny.en" # Model size for faster-whisper

    # ── Security / JWT ───────────────────────────────────────────────
    JWT_SECRET: str = "voxguard-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # ── Supabase ─────────────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Privacy ──────────────────────────────────────────────────────
    ENABLE_PII_MASKING: bool = True    # SHA-256 hash session/phone IDs
    ZERO_RETENTION: bool = True        # Never persist raw audio to disk

    # ── Paths ────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DEMO_AUDIO_DIR: Optional[str] = None  # Directory with demo WAV files

    @property
    def chunk_samples(self) -> int:
        """Number of audio samples in one sliding window."""
        return int(self.SAMPLE_RATE * self.CHUNK_DURATION_S)

    @property
    def hop_samples(self) -> int:
        """Number of audio samples to advance per hop."""
        return int(self.SAMPLE_RATE * self.HOP_DURATION_S)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
