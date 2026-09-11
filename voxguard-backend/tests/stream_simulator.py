"""
VoxGuard Engine — Stream Simulator Test Harness

Generates synthetic and authentic audio test signals and streams them
through the WebSocket endpoint to benchmark latency, accuracy, and
false-positive rates.

Usage::

    # Start the backend first:
    uvicorn app.main:app --port 8000

    # Then run:
    python tests/stream_simulator.py
"""

from __future__ import annotations

import asyncio
import json
import struct
import sys
import time
from pathlib import Path

import numpy as np

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import websockets


# ── Test Signal Generators ───────────────────────────────────────────

def generate_authentic_speech(
    duration_s: float = 3.0,
    sr: int = 16000,
) -> np.ndarray:
    """Generate a realistic speech-like signal with natural characteristics.

    Uses multiple formants, amplitude modulation, and noise to mimic
    the spectral properties of human speech.
    """
    t = np.linspace(0, duration_s, int(sr * duration_s), dtype=np.float32)

    # Fundamental frequency with vibrato
    f0 = 150 + 8 * np.sin(2 * np.pi * 5.5 * t)

    # Formants (typical for vowel /a/)
    signal = np.zeros_like(t)
    formants = [
        (f0, 0.5),      # F0 — fundamental
        (730, 0.3),      # F1
        (1090, 0.2),     # F2
        (2440, 0.08),    # F3
        (3400, 0.03),    # F4 — high-frequency presence
    ]
    for freq, amp in formants:
        signal += amp * np.sin(2 * np.pi * freq * t)

    # Natural amplitude modulation (syllable-like envelope)
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t)
    envelope *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.8 * t)
    signal *= envelope

    # Add aspiration noise (breathy quality)
    noise = np.random.randn(len(t)).astype(np.float32) * 0.03
    signal += noise

    # Normalise
    signal = signal / (np.max(np.abs(signal)) + 1e-8) * 0.7
    return signal


def generate_synthetic_clone(
    duration_s: float = 3.0,
    sr: int = 16000,
) -> np.ndarray:
    """Generate a synthetic vocoder-like signal with typical artefacts.

    Characteristics that trigger DSP detection:
    - Flat spectral energy distribution
    - Abrupt phase resets
    - Low dynamic range
    - Absence of natural high-frequency decay
    """
    t = np.linspace(0, duration_s, int(sr * duration_s), dtype=np.float32)

    # Harmonically rich but unnaturally flat signal
    signal = np.zeros_like(t)
    for harmonic in range(1, 25):
        # Flat amplitudes across harmonics (unnatural)
        amp = 0.04
        freq = 180 * harmonic
        if freq > sr / 2:
            break
        signal += amp * np.sin(2 * np.pi * freq * t)

    # Add vocoder frame artefact: periodic phase resets
    frame_size = int(0.02 * sr)  # 20ms frames
    for i in range(0, len(signal), frame_size):
        end = min(i + frame_size, len(signal))
        # Apply rectangular window (creates discontinuities)
        signal[i:end] *= 0.95

    # Very low dynamic range (compressed)
    signal = np.tanh(signal * 5) * 0.3

    # No natural noise floor — too clean
    return signal.astype(np.float32)


def audio_to_pcm_int16_bytes(audio: np.ndarray) -> bytes:
    """Convert float32 audio to PCM Int16 bytes."""
    int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    return int16.tobytes()


# ── WebSocket Streaming ──────────────────────────────────────────────

async def stream_audio_and_collect_results(
    uri: str,
    audio: np.ndarray,
    label: str,
    chunk_duration_s: float = 0.1,
    sr: int = 16000,
) -> list[dict]:
    """Stream audio through the WebSocket and collect detection results.

    Args:
        uri: WebSocket endpoint URI.
        audio: Float32 audio array.
        label: "authentic" or "synthetic" — for result annotation.
        chunk_duration_s: Duration of each sent chunk.
        sr: Sample rate.

    Returns:
        List of detection result dicts.
    """
    results = []
    chunk_size = int(sr * chunk_duration_s)
    pcm_bytes = audio_to_pcm_int16_bytes(audio)
    chunk_byte_size = chunk_size * 2  # 2 bytes per Int16 sample

    try:
        async with websockets.connect(uri, max_size=2**20) as ws:
            # Wait for connection confirmation
            init_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            init_data = json.loads(init_msg)
            print(f"  Connected: {init_data.get('type', 'unknown')}")

            # Stream audio in chunks
            offset = 0
            send_count = 0
            while offset < len(pcm_bytes):
                chunk = pcm_bytes[offset: offset + chunk_byte_size]
                await ws.send(chunk)
                offset += chunk_byte_size
                send_count += 1

                # Small delay to simulate real-time streaming
                await asyncio.sleep(chunk_duration_s * 0.5)

                # Non-blocking receive
                try:
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.05)
                        data = json.loads(response)
                        if data.get("type") == "detection_result" and data.get("result"):
                            data["result"]["_label"] = label
                            results.append(data["result"])
                except (asyncio.TimeoutError, Exception):
                    pass

            # Drain remaining results
            await asyncio.sleep(1.0)
            try:
                while True:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    data = json.loads(response)
                    if data.get("type") == "detection_result" and data.get("result"):
                        data["result"]["_label"] = label
                        results.append(data["result"])
            except (asyncio.TimeoutError, Exception):
                pass

    except Exception as e:
        print(f"  ⚠ Connection error: {e}")

    return results


# ── Benchmark Runner ─────────────────────────────────────────────────

async def run_benchmark(host: str = "localhost", port: int = 8000) -> None:
    """Run the full benchmark suite and print a formatted report."""
    base_uri = f"ws://{host}:{port}/ws/live-stream"

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         VoxGuard Engine — Stream Simulator Benchmark        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    test_cases = [
        ("authentic_1", "authentic", generate_authentic_speech(3.0)),
        ("authentic_2", "authentic", generate_authentic_speech(4.0)),
        ("synthetic_1", "synthetic", generate_synthetic_clone(3.0)),
        ("synthetic_2", "synthetic", generate_synthetic_clone(4.0)),
    ]

    all_results: list[dict] = []

    for session_name, label, audio in test_cases:
        uri = f"{base_uri}/{session_name}"
        print(f"▸ Streaming [{label.upper():>10}] — session: {session_name} ({len(audio)/16000:.1f}s)")

        results = await stream_audio_and_collect_results(uri, audio, label)
        all_results.extend(results)

        for r in results:
            verdict = r.get("verdict", "?")
            confidence = r.get("confidence", 0)
            latency = r.get("latency_ms", 0)
            flags = r.get("anomaly_flags", [])
            icon = "🟢" if verdict == "human" else "🔴" if verdict == "synthetic" else "🟡"
            print(
                f"  {icon} verdict={verdict:<10} confidence={confidence:.3f} "
                f"latency={latency:.1f}ms flags={flags}"
            )

        print()

    # ── Report ───────────────────────────────────────────────────────
    if not all_results:
        print("⚠ No results collected. Is the backend running?")
        return

    print("═" * 60)
    print("BENCHMARK REPORT")
    print("═" * 60)

    # Accuracy
    correct = 0
    total = len(all_results)
    tp = fp = tn = fn = 0

    for r in all_results:
        label = r.get("_label", "")
        is_synth = r.get("is_synthetic", False)

        if label == "synthetic" and is_synth:
            tp += 1; correct += 1
        elif label == "authentic" and not is_synth:
            tn += 1; correct += 1
        elif label == "authentic" and is_synth:
            fp += 1
        elif label == "synthetic" and not is_synth:
            fn += 1

    accuracy = correct / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Latency
    latencies = [r.get("latency_ms", 0) for r in all_results]
    avg_lat = np.mean(latencies)
    p95_lat = np.percentile(latencies, 95)
    max_lat = np.max(latencies)

    print(f"  Total chunks analysed : {total}")
    print(f"  True Positives (TP)   : {tp}")
    print(f"  True Negatives (TN)   : {tn}")
    print(f"  False Positives (FP)  : {fp}")
    print(f"  False Negatives (FN)  : {fn}")
    print(f"  Accuracy              : {accuracy:.1%}")
    print(f"  Precision             : {precision:.1%}")
    print(f"  Recall                : {recall:.1%}")
    print(f"  F1 Score              : {f1:.3f}")
    print()
    print(f"  Avg Latency           : {avg_lat:.1f} ms")
    print(f"  P95 Latency           : {p95_lat:.1f} ms")
    print(f"  Max Latency           : {max_lat:.1f} ms")
    print(f"  < 200ms target met    : {'✅ YES' if p95_lat < 200 else '❌ NO'}")
    print(f"  False Positive Rate   : {fp/(fp+tn)*100 if (fp+tn) > 0 else 0:.1f}%")
    print("═" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VoxGuard Stream Simulator")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.host, args.port))
