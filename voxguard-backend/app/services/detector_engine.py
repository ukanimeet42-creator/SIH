"""
VoxGuard Engine — Detector Engine

Two-tier detection architecture:

1. **DSP Heuristic Pipeline** (always active, zero model weight):
   Deterministic classification based on spectral flatness, high-frequency
   rolloff, zero-crossing rate, Mel-energy variance, phase discontinuity,
   and dynamic range.  Produces a composite confidence score via weighted
   voting of anomaly indicators.

2. **ONNX Model Pipeline** (optional, ~40–80 MB):
   Loads a pre-trained anti-spoofing model (AASIST / AST ONNX export) for
   learned feature classification.  When available, the DSP and model scores
   are fused for higher accuracy.

No random noise is used anywhere.  All scores are deterministic given the
same input audio.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import get_settings
from app.models.schemas import AnomalyFlag, DetectionResult, DetectionVerdict
from app.services.feature_extractor import SpectralFeatures, extract_all_features

logger = logging.getLogger(__name__)
_settings = get_settings()


# ── Anomaly Weights for DSP Heuristic ────────────────────────────────
# Each anomaly flag contributes a weighted vote toward the "synthetic"
# classification.  Weights sum to ~1.0 so the raw DSP score lives in [0, 1].

_ANOMALY_WEIGHTS: dict[AnomalyFlag, float] = {
    AnomalyFlag.SPECTRAL_FLATNESS:    0.22,
    AnomalyFlag.HF_ROLLOFF:           0.20,
    AnomalyFlag.PHASE_DISCONTINUITY:  0.20,
    AnomalyFlag.ZCR_ANOMALY:          0.10,
    AnomalyFlag.MEL_ENERGY_FLAT:      0.18,
    AnomalyFlag.LOW_DYNAMIC_RANGE:    0.10,
}


class DetectorEngine:
    """Singleton detector combining DSP heuristics + optional ONNX model.

    Usage::

        engine = DetectorEngine()
        await engine.initialise()
        result = engine.predict_chunk(audio_array)
    """

    _instance: Optional["DetectorEngine"] = None

    def __new__(cls) -> "DetectorEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    async def initialise(self) -> None:
        """Load the ONNX model if configured, otherwise DSP-only mode."""
        if self._initialised:
            return

        self._onnx_session = None

        if _settings.USE_ONNX and _settings.MODEL_PATH:
            model_path = Path(_settings.MODEL_PATH)
            if model_path.exists():
                try:
                    import onnxruntime as ort

                    sess_opts = ort.SessionOptions()
                    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    sess_opts.intra_op_num_threads = 2

                    providers = ["CPUExecutionProvider"]
                    # Try GPU if available
                    available = ort.get_available_providers()
                    if "CUDAExecutionProvider" in available:
                        providers.insert(0, "CUDAExecutionProvider")

                    self._onnx_session = ort.InferenceSession(
                        str(model_path), sess_options=sess_opts, providers=providers,
                    )
                    input_meta = self._onnx_session.get_inputs()
                    output_meta = self._onnx_session.get_outputs()
                    logger.info(
                        "ONNX model loaded: %s — inputs=%s, outputs=%s, providers=%s",
                        model_path.name,
                        [i.name for i in input_meta],
                        [o.name for o in output_meta],
                        self._onnx_session.get_providers(),
                    )
                except Exception:
                    logger.exception("Failed to load ONNX model at %s, falling back to DSP-only", model_path)
            else:
                logger.warning("ONNX model path %s does not exist — DSP-only mode", model_path)

        mode = "ONNX + DSP fusion" if self._onnx_session else "DSP heuristic only"
        logger.info("DetectorEngine initialised in %s mode", mode)
        self._initialised = True

    # ── Core Prediction ──────────────────────────────────────────────

    def predict_chunk(self, audio: np.ndarray, sr: int = _settings.SAMPLE_RATE) -> DetectionResult:
        """Analyse a single audio window and return a detection result.

        Pipeline:
        1. Extract spectral features (deterministic DSP).
        2. Compute DSP heuristic score from anomaly flags.
        3. If ONNX model is loaded, run model inference and fuse scores.
        4. Apply threshold → verdict.

        Args:
            audio: 1-D float32 mono audio array.
            sr: Sample rate.

        Returns:
            Fully populated :class:`DetectionResult`.
        """
        t0 = time.perf_counter()

        # 1. Feature extraction
        features = extract_all_features(audio, sr)

        # 2. DSP heuristic score
        dsp_score = self._compute_dsp_score(features)

        # 3. Optional ONNX model score
        model_score: Optional[float] = None
        if self._onnx_session is not None:
            model_score = self._run_onnx_inference(audio, features)

        # 4. Fuse scores
        if model_score is not None:
            # Weighted average: 60% model, 40% DSP
            confidence = 0.60 * model_score + 0.40 * dsp_score
        else:
            confidence = dsp_score

        confidence = float(np.clip(confidence, 0.0, 1.0))

        # 5. Verdict
        if confidence >= _settings.DETECTION_THRESHOLD:
            verdict = DetectionVerdict.SYNTHETIC
        elif confidence >= _settings.DETECTION_THRESHOLD * 0.6:
            verdict = DetectionVerdict.UNCERTAIN
        else:
            verdict = DetectionVerdict.HUMAN

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return DetectionResult(
            is_synthetic=verdict == DetectionVerdict.SYNTHETIC,
            confidence=round(confidence, 4),
            verdict=verdict,
            anomaly_flags=features.anomaly_flags,
            latency_ms=round(latency_ms, 2),
            spectral_flatness=round(features.spectral_flatness, 4),
            spectral_centroid_hz=round(features.spectral_centroid_hz, 2),
            hf_energy_ratio=round(features.hf_energy_ratio, 4),
        )

    # ── DSP Heuristic Scoring ────────────────────────────────────────

    @staticmethod
    def _compute_dsp_score(features: SpectralFeatures) -> float:
        """Compute a deterministic synthetic-confidence score from DSP features.

        The score is a weighted sum of triggered anomaly flags, with continuous
        modifiers from spectral flatness and phase discontinuity to provide
        gradient sensitivity (not just binary flags).

        Returns:
            Score in [0, 1] — higher means more likely synthetic.
        """
        # Base score from binary anomaly flags
        base_score = sum(
            _ANOMALY_WEIGHTS.get(flag, 0.0) for flag in features.anomaly_flags
        )

        # Continuous modifiers for gradient sensitivity
        # Spectral flatness: map from [0, 1] with a sigmoid-like curve
        flatness_mod = _sigmoid(features.spectral_flatness, center=0.25, steepness=12) * 0.15

        # Phase discontinuity: linear contribution
        phase_mod = features.phase_discontinuity_score * 0.10

        # HF energy: penalise both absence and excess
        hf_deviation = abs(features.hf_energy_ratio - 0.08)  # 0.08 is typical for speech
        hf_mod = min(hf_deviation * 2.0, 0.10)

        score = base_score + flatness_mod + phase_mod + hf_mod
        return float(np.clip(score, 0.0, 1.0))

    # ── ONNX Inference ───────────────────────────────────────────────

    def _run_onnx_inference(self, audio: np.ndarray, features: SpectralFeatures) -> float:
        """Run the ONNX anti-spoofing model on the audio chunk.

        Handles both raw-waveform models (AASIST-style: input shape [1, T])
        and feature-based models (input shape [1, n_features, T]).

        Returns:
            Synthetic probability in [0, 1].
        """
        if self._onnx_session is None:
            return 0.0

        try:
            input_meta = self._onnx_session.get_inputs()[0]
            input_name = input_meta.name
            input_shape = input_meta.shape

            # Determine input format
            if len(input_shape) == 2:
                # Raw waveform: [batch, samples]
                input_data = audio.reshape(1, -1).astype(np.float32)
                # Pad or truncate to expected length if specified
                if isinstance(input_shape[1], int) and input_shape[1] > 0:
                    target_len = input_shape[1]
                    if input_data.shape[1] < target_len:
                        input_data = np.pad(input_data, ((0, 0), (0, target_len - input_data.shape[1])))
                    else:
                        input_data = input_data[:, :target_len]
            else:
                # Feature-based: use MFCC [batch, n_mfcc, T]
                input_data = features.mfcc.reshape(1, *features.mfcc.shape).astype(np.float32)

            outputs = self._onnx_session.run(None, {input_name: input_data})
            logits = outputs[0]

            # Handle different output formats
            if logits.shape[-1] == 2:
                # Binary classification [genuine, spoof]
                from scipy.special import softmax
                probs = softmax(logits[0])
                return float(probs[1])  # spoof probability
            elif logits.shape[-1] == 1:
                # Single score
                return float(1.0 / (1.0 + np.exp(-logits[0][0])))  # sigmoid
            else:
                return float(logits[0][0])

        except Exception:
            logger.exception("ONNX inference failed, falling back to DSP-only score")
            return 0.0


# ── Utility ──────────────────────────────────────────────────────────

def _sigmoid(x: float, center: float = 0.0, steepness: float = 1.0) -> float:
    """Numerically stable sigmoid with adjustable center and steepness."""
    z = steepness * (x - center)
    if z >= 0:
        return 1.0 / (1.0 + np.exp(-z))
    else:
        ez = np.exp(z)
        return ez / (1.0 + ez)
