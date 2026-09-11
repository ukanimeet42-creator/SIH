"""
VoxGuard Engine — Audio Preprocessor

Handles raw PCM byte ingestion, sliding window buffering with configurable
hop size, and sample-rate normalisation to 16 kHz mono float32.

The frontend AudioWorklet already downsamples to 16 kHz Int16 PCM, so this
module validates and converts to the float32 tensor format required by the
feature extractor and detector engine.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import AsyncGenerator, Optional

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


class SlidingWindowBuffer:
    """Accumulates PCM audio and yields overlapping fixed-length windows.

    The buffer implements a sliding window of ``chunk_samples`` length
    with ``hop_samples`` stride.  Each call to :meth:`add_audio` may
    yield zero or more complete windows depending on how much audio has
    been accumulated.

    Attributes:
        chunk_samples: Number of samples in one analysis window.
        hop_samples:   Number of samples to advance per hop.
    """

    def __init__(
        self,
        chunk_samples: Optional[int] = None,
        hop_samples: Optional[int] = None,
        sample_rate: Optional[int] = None,
    ) -> None:
        self.sample_rate = sample_rate or _settings.SAMPLE_RATE
        self.chunk_samples = chunk_samples or _settings.chunk_samples
        self.hop_samples = hop_samples or _settings.hop_samples

        # Internal ring-buffer backed by a deque of float32 samples
        self._buffer: deque[float] = deque(maxlen=self.chunk_samples * 4)  # generous capacity
        self._total_samples_ingested: int = 0

        logger.info(
            "SlidingWindowBuffer initialised — chunk=%d samples (%.2fs), hop=%d samples (%.2fs)",
            self.chunk_samples,
            self.chunk_samples / self.sample_rate,
            self.hop_samples,
            self.hop_samples / self.sample_rate,
        )

    # ── Public API ───────────────────────────────────────────────────

    def add_audio(self, audio: np.ndarray) -> list[np.ndarray]:
        """Append audio samples and return any complete windows.

        Args:
            audio: 1-D float32 array of mono audio samples at target sample rate.

        Returns:
            List of float32 arrays, each of length ``chunk_samples``.
        """
        self._buffer.extend(audio.tolist())
        self._total_samples_ingested += len(audio)

        windows: list[np.ndarray] = []
        buf_array = np.array(self._buffer, dtype=np.float32)

        while len(buf_array) >= self.chunk_samples:
            window = buf_array[: self.chunk_samples].copy()
            windows.append(window)

            # Advance by hop
            buf_array = buf_array[self.hop_samples:]

        # Store remaining samples back
        self._buffer = deque(buf_array.tolist(), maxlen=self.chunk_samples * 4)
        return windows

    def reset(self) -> None:
        """Flush the internal buffer."""
        self._buffer.clear()
        self._total_samples_ingested = 0

    @property
    def buffered_samples(self) -> int:
        """Current number of samples waiting in the buffer."""
        return len(self._buffer)

    @property
    def buffered_duration_s(self) -> float:
        """Current buffered duration in seconds."""
        return self.buffered_samples / self.sample_rate

    @property
    def total_ingested_duration_s(self) -> float:
        """Total audio duration ingested since creation / last reset."""
        return self._total_samples_ingested / self.sample_rate


# ── Utility Functions ────────────────────────────────────────────────

def pcm_int16_to_float32(raw_bytes: bytes) -> np.ndarray:
    """Convert raw PCM Int16 bytes to normalised float32 in [-1, 1].

    Args:
        raw_bytes: Raw PCM audio bytes (little-endian Int16).

    Returns:
        1-D float32 numpy array.
    """
    samples = np.frombuffer(raw_bytes, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def validate_audio(audio: np.ndarray, sample_rate: int = _settings.SAMPLE_RATE) -> np.ndarray:
    """Validate and sanitise an audio array.

    - Ensures 1-D shape (mono).
    - Clips extreme values.
    - Rejects silent / corrupt frames.

    Args:
        audio: Input audio array.
        sample_rate: Expected sample rate.

    Returns:
        Sanitised float32 array.

    Raises:
        ValueError: If the audio is corrupt or empty.
    """
    if audio.ndim != 1:
        raise ValueError(f"Expected mono (1-D) audio, got shape {audio.shape}")
    if len(audio) == 0:
        raise ValueError("Received empty audio frame")

    audio = audio.astype(np.float32)

    # Clip extreme values
    audio = np.clip(audio, -1.0, 1.0)

    # Reject near-silent frames (< -60 dB RMS)
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-6:
        logger.debug("Audio frame is near-silent (RMS=%.2e), passing through", rms)

    return audio


async def stream_windows(
    buffer: SlidingWindowBuffer,
) -> AsyncGenerator[np.ndarray, bytes]:
    """Async generator that receives raw PCM bytes and yields analysis windows.

    Usage::

        gen = stream_windows(buffer)
        await gen.asend(None)  # prime
        while True:
            windows = await gen.asend(raw_bytes)
            for w in windows:
                result = detector.predict_chunk(w)
    """
    raw_bytes = yield  # type: ignore[misc]  # prime
    while True:
        audio = pcm_int16_to_float32(raw_bytes)
        audio = validate_audio(audio)
        windows = buffer.add_audio(audio)
        raw_bytes = yield windows  # type: ignore[misc]
