"""
VoxGuard Engine — Prevention Service

Dynamic Voice CAPTCHA challenge generator and verifier.

Challenge generation uses a curated word bank with phonetically rich,
unpredictable phrases designed to defeat automated conversational clones.

Verification supports two backends:
  1. **Backend STT** — ``faster-whisper`` (``tiny.en`` model, ~39 MB)
     running server-side for language-agnostic verification.
  2. **Frontend STT** — The browser's Web Speech API
     (``webkitSpeechRecognition``) handles recognition client-side and
     sends the transcript text to the backend for matching.

Both paths converge on the same fuzzy string matching logic.
"""

from __future__ import annotations

import io
import logging
import random
import re
from difflib import SequenceMatcher
from typing import Optional

import numpy as np

from app.core.config import get_settings
from app.models.schemas import ChallengeResponse

logger = logging.getLogger(__name__)
_settings = get_settings()


# ── Word Banks ───────────────────────────────────────────────────────
# Designed for phonetic richness: consonant clusters, plosives, fricatives,
# nasals, rare vowel combos, and mixed numeric tokens.

_ADJECTIVES = [
    "azure", "crimson", "jagged", "obsidian", "phosphorescent", "viridian",
    "quartz", "frozen", "splintered", "gossamer", "trembling", "iridescent",
    "cobalt", "fractured", "luminous", "serpentine", "thunderous", "crystalline",
]

_NOUNS = [
    "hawk", "glacier", "sphinx", "prism", "canyon", "vortex", "compass",
    "chrysalis", "labyrinth", "zenith", "eclipse", "fjord", "nebula",
    "obelisk", "phantom", "tempest", "archipelago", "cascade",
]

_VERBS = [
    "flew", "shattered", "whispered", "plunged", "scattered", "etched",
    "traversed", "dissolved", "illuminated", "fractured", "engulfed",
    "spiralled", "reverberated", "crystallised", "manifested",
]

_ADVERBS = [
    "swiftly", "abruptly", "gracefully", "precisely", "obliquely",
    "methodically", "relentlessly", "silently", "thunderously",
]

_PREPOSITIONS = [
    "through", "beneath", "beyond", "across", "against", "within", "past",
    "alongside", "amid", "toward",
]


# ── Challenge Generation ────────────────────────────────────────────

def generate_challenge_phrase() -> str:
    """Generate a phonetically rich, unpredictable challenge sentence.

    The phrase structure is:
        ``"The {adj} {noun} {verb} {adv} {prep} {number}"``

    The numeric token defeats simple text-to-speech replay because the
    spoken form of numbers varies (e.g., "482" → "four eighty-two" or
    "four hundred and eighty-two").

    Returns:
        A challenge phrase string, e.g. "The azure sphinx traversed
        swiftly past 738".
    """
    adj = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    verb = random.choice(_VERBS)
    adv = random.choice(_ADVERBS)
    prep = random.choice(_PREPOSITIONS)
    number = random.randint(100, 999)

    phrase = f"The {adj} {noun} {verb} {adv} {prep} {number}"
    logger.info("Generated challenge phrase: %s", phrase)
    return phrase


# ── Transcript Matching ─────────────────────────────────────────────

def _normalise_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _number_to_words(n: int) -> str:
    """Convert a 3-digit integer to its spoken English form.

    Handles the common STT transcription variants.
    """
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = [
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

    if n < 10:
        return ones[n]
    elif n < 20:
        return teens[n - 10]
    elif n < 100:
        return tens[n // 10] + ("" if n % 10 == 0 else " " + ones[n % 10])
    else:
        result = ones[n // 100] + " hundred"
        remainder = n % 100
        if remainder:
            result += " and " + _number_to_words(remainder)
        return result


def _expand_numbers_in_text(text: str) -> str:
    """Replace digit sequences with their spoken English form."""
    def _replace(match):
        return _number_to_words(int(match.group()))
    return re.sub(r"\d+", _replace, text)


def compute_phrase_similarity(recognised: str, target: str) -> float:
    """Compute fuzzy similarity between recognised and target phrases.

    Handles number representation variants by comparing both digit and
    word forms.

    Args:
        recognised: The STT-transcribed text.
        target: The original challenge phrase.

    Returns:
        Similarity score in [0, 1].
    """
    norm_recognised = _normalise_text(recognised)
    norm_target = _normalise_text(target)

    # Direct comparison
    direct = SequenceMatcher(None, norm_recognised, norm_target).ratio()

    # Expanded-number comparison (e.g., "482" → "four hundred and eighty two")
    expanded_target = _normalise_text(_expand_numbers_in_text(target))
    expanded_recognised = _normalise_text(_expand_numbers_in_text(recognised))
    expanded = SequenceMatcher(None, expanded_recognised, expanded_target).ratio()

    return max(direct, expanded)


# ── Challenge Verification ──────────────────────────────────────────

# Lazy-loaded whisper model
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the faster-whisper model on first use."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Loading faster-whisper model: %s", _settings.WHISPER_MODEL_SIZE)
            _whisper_model = WhisperModel(
                _settings.WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",
            )
            logger.info("faster-whisper model loaded successfully")
        except ImportError:
            logger.warning("faster-whisper not installed — backend STT disabled")
        except Exception:
            logger.exception("Failed to load faster-whisper model")
    return _whisper_model


def transcribe_audio_backend(audio: np.ndarray, sr: int = 16000) -> str:
    """Transcribe audio using faster-whisper (backend STT).

    Args:
        audio: 1-D float32 mono audio array at ``sr``.
        sr: Sample rate.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    model = _get_whisper_model()
    if model is None:
        logger.error("Whisper model not available for transcription")
        return ""

    try:
        import soundfile as sf

        # faster-whisper expects a file path or file-like object
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        buf.seek(0)

        segments, info = model.transcribe(
            buf,
            language="en",
            beam_size=1,         # Speed over accuracy for challenge verification
            vad_filter=True,
        )
        transcript = " ".join(seg.text.strip() for seg in segments)
        logger.info("Backend STT transcript: %s", transcript)
        return transcript

    except Exception:
        logger.exception("Backend STT transcription failed")
        return ""


async def verify_challenge_response(
    target_phrase: str,
    recognised_text: Optional[str] = None,
    audio: Optional[np.ndarray] = None,
    sr: int = 16000,
    similarity_threshold: float = 0.70,
) -> ChallengeResponse:
    """Verify a spoken challenge response against the target phrase.

    Supports two verification paths:

    1. **Frontend-STT path**: ``recognised_text`` is provided by the browser's
       Web Speech API — just do string matching.
    2. **Backend-STT path**: ``audio`` is provided and transcribed server-side
       via faster-whisper before matching.

    Args:
        target_phrase: The original challenge phrase.
        recognised_text: Transcript from browser Web Speech API (optional).
        audio: Raw float32 audio for server-side transcription (optional).
        sr: Sample rate for server-side audio.
        similarity_threshold: Minimum similarity score to pass.

    Returns:
        :class:`ChallengeResponse` with match result and scores.

    Raises:
        ValueError: If neither ``recognised_text`` nor ``audio`` is provided.
    """
    if recognised_text is None and audio is None:
        raise ValueError("Provide either recognised_text or audio for verification")

    # Transcribe if needed
    if recognised_text is None and audio is not None:
        recognised_text = transcribe_audio_backend(audio, sr)

    if not recognised_text:
        return ChallengeResponse(
            matched=False,
            expected_phrase=target_phrase,
            recognised_text="",
            similarity_score=0.0,
        )

    similarity = compute_phrase_similarity(recognised_text, target_phrase)
    matched = similarity >= similarity_threshold

    logger.info(
        "Challenge verification — target=%r, recognised=%r, similarity=%.3f, matched=%s",
        target_phrase, recognised_text, similarity, matched,
    )

    return ChallengeResponse(
        matched=matched,
        expected_phrase=target_phrase,
        recognised_text=recognised_text,
        similarity_score=round(similarity, 4),
    )
