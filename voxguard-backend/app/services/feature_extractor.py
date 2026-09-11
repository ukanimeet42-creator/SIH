"""
VoxGuard Engine — Spectral Feature Extractor

Pure-DSP feature extraction using ``librosa`` and ``numpy``.  Provides
LFCC, MFCC, spectral centroid / rolloff / flatness, zero-crossing rate,
Mel-energy distribution analysis, and vocoder phase-discontinuity detection.

All functions are deterministic — no randomness, no model weights.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import librosa
import numpy as np

from app.core.config import get_settings
from app.models.schemas import AnomalyFlag

logger = logging.getLogger(__name__)
_settings = get_settings()


@dataclass
class SpectralFeatures:
    """Container for all extracted spectral features."""

    lfcc: np.ndarray = field(default_factory=lambda: np.array([]))
    mfcc: np.ndarray = field(default_factory=lambda: np.array([]))
    mel_spectrogram: np.ndarray = field(default_factory=lambda: np.array([]))
    spectral_flatness: float = 0.0
    spectral_centroid_hz: float = 0.0
    spectral_rolloff_hz: float = 0.0
    hf_energy_ratio: float = 0.0       # Energy > 8 kHz / total energy
    zero_crossing_rate: float = 0.0
    mel_energy_variance: float = 0.0
    dynamic_range_db: float = 0.0
    phase_discontinuity_score: float = 0.0
    anomaly_flags: List[AnomalyFlag] = field(default_factory=list)


# ── Feature Extraction Functions ─────────────────────────────────────

def extract_lfcc(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    n_lfcc: int = 20,
    n_fft: int = 512,
    hop_length: int = 160,
) -> np.ndarray:
    """Extract Linear Frequency Cepstral Coefficients (LFCC).

    LFCCs use a linearly-spaced filterbank (unlike MFCCs which use Mel scale).
    They are more sensitive to high-frequency artefacts common in vocoder output.

    Args:
        audio: 1-D float32 mono audio at ``sr``.
        sr: Sample rate.
        n_lfcc: Number of LFCC coefficients.
        n_fft: FFT window size.
        hop_length: Hop length for STFT.

    Returns:
        2-D array of shape ``(n_lfcc, T)`` where ``T`` is the number of frames.
    """
    # Compute power spectrum
    S = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)) ** 2

    # Linear filterbank (evenly spaced)
    n_filters = n_lfcc * 2
    freq_bins = S.shape[0]
    filterbank = np.zeros((n_filters, freq_bins))

    bin_edges = np.linspace(0, freq_bins - 1, n_filters + 2, dtype=int)
    for i in range(n_filters):
        start, center, end = bin_edges[i], bin_edges[i + 1], bin_edges[i + 2]
        for j in range(start, center):
            if center != start:
                filterbank[i, j] = (j - start) / (center - start)
        for j in range(center, end):
            if end != center:
                filterbank[i, j] = (end - j) / (end - center)

    # Apply filterbank and take log
    filter_energies = np.dot(filterbank, S)
    filter_energies = np.maximum(filter_energies, 1e-10)
    log_energies = np.log(filter_energies)

    # DCT to get cepstral coefficients
    from scipy.fft import dct
    lfcc = dct(log_energies, type=2, axis=0, norm="ortho")[:n_lfcc]

    return lfcc


def extract_mfcc(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    n_mfcc: int = 20,
    n_fft: int = 512,
    hop_length: int = 160,
) -> np.ndarray:
    """Extract Mel-Frequency Cepstral Coefficients via librosa.

    Args:
        audio: 1-D float32 mono audio at ``sr``.
        sr: Sample rate.
        n_mfcc: Number of MFCC coefficients.

    Returns:
        2-D array of shape ``(n_mfcc, T)``.
    """
    return librosa.feature.mfcc(
        y=audio, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length,
    )


def extract_mel_spectrogram_db(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    n_mels: int = 128,
    n_fft: int = 512,
    hop_length: int = 160,
) -> np.ndarray:
    """Extract Log-Mel Spectrogram for AASIST / LCNN compatibility.

    Returns:
        2-D array of shape ``(n_mels, T)`` in decibels.
    """
    mel_spec = librosa.feature.melspectrogram(
        y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels
    )
    return librosa.power_to_db(mel_spec, ref=np.max)



def compute_spectral_flatness(audio: np.ndarray, sr: int = _settings.SAMPLE_RATE) -> float:
    """Wiener entropy / spectral flatness — ratio of geometric to arithmetic mean.

    Values close to 1.0 indicate a flat (noise-like) spectrum, common in
    vocoder artefacts.  Natural speech is typically 0.01–0.2.

    Returns:
        Mean spectral flatness across all frames.
    """
    sf = librosa.feature.spectral_flatness(y=audio)
    return float(np.mean(sf))


def compute_spectral_centroid(audio: np.ndarray, sr: int = _settings.SAMPLE_RATE) -> float:
    """Spectral centroid in Hz — the "brightness" of the signal.

    Returns:
        Mean spectral centroid across all frames.
    """
    sc = librosa.feature.spectral_centroid(y=audio, sr=sr)
    return float(np.mean(sc))


def compute_spectral_rolloff(audio: np.ndarray, sr: int = _settings.SAMPLE_RATE) -> float:
    """Spectral rolloff frequency in Hz — frequency below which N% of energy lies.

    Returns:
        Mean rolloff frequency.
    """
    ro = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)
    return float(np.mean(ro))


def compute_zero_crossing_rate(audio: np.ndarray) -> float:
    """Mean zero-crossing rate across all frames.

    Returns:
        Mean ZCR value.
    """
    zcr = librosa.feature.zero_crossing_rate(audio)
    return float(np.mean(zcr))


def compute_hf_energy_ratio(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    cutoff_hz: int = 6000,  # lowered to 6000Hz since 16kHz sr Nyquist is 8000Hz
    n_fft: int = 512,
) -> float:
    """Ratio of spectral energy above ``cutoff_hz`` to total energy.

    Vocoders often produce unnaturally flat or absent high-frequency content,
    or conversely inject artefacts above the cutoff.

    Returns:
        Ratio in [0, 1].
    """
    S = np.abs(librosa.stft(audio, n_fft=n_fft)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    cutoff_bin = np.searchsorted(freqs, cutoff_hz)
    total_energy = np.sum(S)
    if total_energy < 1e-12:
        return 0.0

    hf_energy = np.sum(S[cutoff_bin:, :])
    return float(hf_energy / total_energy)


def compute_mel_energy_variance(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    n_mels: int = 40,
) -> float:
    """Variance of Mel-band energies — low variance indicates vocoder output.

    Returns:
        Normalised variance across Mel bands.
    """
    mel_spec = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=n_mels)
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    band_means = np.mean(mel_db, axis=1)  # mean energy per band
    return float(np.var(band_means) / (np.max(np.abs(band_means)) + 1e-10))


def compute_dynamic_range(audio: np.ndarray) -> float:
    """Dynamic range in dB — difference between peak and RMS levels.

    Returns:
        Dynamic range in dB.
    """
    rms = np.sqrt(np.mean(audio ** 2))
    peak = np.max(np.abs(audio))
    if rms < 1e-10 or peak < 1e-10:
        return 0.0
    return float(20 * np.log10(peak / rms))


def detect_phase_discontinuity(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
    n_fft: int = 512,
    hop_length: int = 160,
) -> float:
    """Detect vocoder phase discontinuities in the STFT.

    Computes the instantaneous frequency deviation from expected linear phase
    progression.  Vocoders often produce abrupt phase jumps at frame boundaries.

    Returns:
        Mean phase deviation score in [0, 1] — higher = more discontinuous.
    """
    S = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    phase = np.angle(S)

    if phase.shape[1] < 3:
        return 0.0

    # Instantaneous frequency via phase differences
    d_phase = np.diff(phase, axis=1)

    # Expected phase advance per hop
    expected_advance = 2 * np.pi * np.arange(phase.shape[0])[:, None] * hop_length / n_fft

    # Deviation from expected
    deviation = np.abs(d_phase - expected_advance[:, : d_phase.shape[1]])
    # Wrap to [-π, π]
    deviation = np.abs(np.arctan2(np.sin(deviation), np.cos(deviation)))

    score = float(np.mean(deviation) / np.pi)  # Normalise to [0, 1]
    return min(score, 1.0)


# ── High-Level Extraction Pipeline ──────────────────────────────────

def extract_all_features(
    audio: np.ndarray,
    sr: int = _settings.SAMPLE_RATE,
) -> SpectralFeatures:
    """Run the full feature extraction pipeline and flag anomalies.

    Args:
        audio: 1-D float32 mono audio at ``sr``.
        sr: Sample rate.

    Returns:
        Populated :class:`SpectralFeatures` with anomaly flags set.
    """
    features = SpectralFeatures()

    # ── Core features ────────────────────────────────────────────────
    features.lfcc = extract_lfcc(audio, sr)
    features.mfcc = extract_mfcc(audio, sr)
    features.mel_spectrogram = extract_mel_spectrogram_db(audio, sr)
    features.spectral_flatness = compute_spectral_flatness(audio, sr)
    features.spectral_centroid_hz = compute_spectral_centroid(audio, sr)
    features.spectral_rolloff_hz = compute_spectral_rolloff(audio, sr)
    features.hf_energy_ratio = compute_hf_energy_ratio(audio, sr)
    features.zero_crossing_rate = compute_zero_crossing_rate(audio)
    features.mel_energy_variance = compute_mel_energy_variance(audio, sr)
    features.dynamic_range_db = compute_dynamic_range(audio)
    features.phase_discontinuity_score = detect_phase_discontinuity(audio, sr)

    # ── Anomaly flagging ─────────────────────────────────────────────
    if features.spectral_flatness > _settings.SPECTRAL_FLATNESS_THRESHOLD:
        features.anomaly_flags.append(AnomalyFlag.SPECTRAL_FLATNESS)

    if features.hf_energy_ratio < 0.01 or features.hf_energy_ratio > _settings.HF_ROLLOFF_THRESHOLD:
        features.anomaly_flags.append(AnomalyFlag.HF_ROLLOFF)

    if features.phase_discontinuity_score > 0.6:
        features.anomaly_flags.append(AnomalyFlag.PHASE_DISCONTINUITY)

    zcr = features.zero_crossing_rate
    if zcr < _settings.ZCR_LOW_THRESHOLD or zcr > _settings.ZCR_HIGH_THRESHOLD:
        features.anomaly_flags.append(AnomalyFlag.ZCR_ANOMALY)

    if features.mel_energy_variance < _settings.MEL_ENERGY_VARIANCE_THRESHOLD:
        features.anomaly_flags.append(AnomalyFlag.MEL_ENERGY_FLAT)

    if features.dynamic_range_db < 6.0:
        features.anomaly_flags.append(AnomalyFlag.LOW_DYNAMIC_RANGE)

    return features
