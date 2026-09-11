"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import WaveformVisualizer from "./WaveformVisualizer";
import ConfidenceGauge from "./ConfidenceGauge";
import ChallengeModal from "./ChallengeModal";
import DemoPresets from "./DemoPresets";
import { useWebSocket, DetectionResult } from "@/hooks/useWebSocket";
import { useAudioCapture } from "@/hooks/useAudioCapture";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/live-stream";

interface LiveAnalysisProps {
  onResult?: (result: DetectionResult) => void;
}

export default function LiveAnalysis({ onResult }: LiveAnalysisProps) {
  const [sessionId, setSessionId] = useState("session-pending");
  const [challengePhrase, setChallengePhrase] = useState<string | null>(null);
  const [challengeResult, setChallengeResult] = useState<{matched: boolean; score: number} | null>(null);
  const [demoStreamingType, setDemoStreamingType] = useState<string | null>(null);

  useEffect(() => {
    setSessionId(`session-${Date.now().toString(36)}`);
  }, []);

  const demoIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket connection
  const ws = useWebSocket({
    url: WS_URL,
    sessionId,
    onResult: (result) => {
      onResult?.(result);
    },
    onChallenge: (phrase) => {
      setChallengePhrase(phrase);
      setChallengeResult(null);
    },
    onChallengeResult: (result: any) => {
      setChallengeResult({
        matched: result.matched,
        score: result.similarity_score,
      });
      if (result.matched) {
        setTimeout(() => setChallengePhrase(null), 2000);
      }
    },
    onError: (err) => {
      console.error("[LiveAnalysis] WS Error:", err);
    },
  });

  // Audio capture
  const audio = useAudioCapture({
    targetSampleRate: 16000,
    bufferSize: 4096,
    onAudioData: (pcmBuffer) => {
      ws.sendAudio(pcmBuffer);
    },
  });

  // Start/stop analysis
  const handleStartAnalysis = useCallback(async () => {
    ws.connect();
    // Small delay for WS connection
    await new Promise((r) => setTimeout(r, 500));
    await audio.startCapture();
  }, [ws, audio]);

  const handleStopAnalysis = useCallback(() => {
    stopDemoStream();
    audio.stopCapture();
    ws.disconnect();
    ws.clearHistory();
  }, [ws, audio]);

  // Demo preset streaming
  const handleDemoPreset = useCallback((type: "authentic" | "synthetic", audioData: ArrayBuffer) => {
    // Make sure WS is connected
    if (ws.status !== "connected") {
      ws.connect();
    }

    setDemoStreamingType(type);

    // Stream the demo audio in chunks (simulating real-time)
    const chunkSize = 4096 * 2; // Int16 = 2 bytes per sample
    let offset = 0;
    const totalBytes = audioData.byteLength;

    demoIntervalRef.current = setInterval(() => {
      if (offset >= totalBytes) {
        stopDemoStream();
        return;
      }

      const end = Math.min(offset + chunkSize, totalBytes);
      const chunk = audioData.slice(offset, end);
      ws.sendAudio(chunk);
      offset = end;
    }, 256); // ~256ms intervals to simulate real-time

  }, [ws]);

  const stopDemoStream = useCallback(() => {
    if (demoIntervalRef.current) {
      clearInterval(demoIntervalRef.current);
      demoIntervalRef.current = null;
    }
    setDemoStreamingType(null);
  }, []);

  const isActive = audio.isCapturing || demoStreamingType !== null;
  const latestResult = ws.latestResult;
  const isThreat = latestResult?.verdict === "synthetic";

  return (
    <div className="space-y-6">
      {/* Control Bar */}
      <div className="glass rounded-2xl p-5 neon-border-cyan flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={`w-3 h-3 rounded-full ${
            ws.status === "connected" ? "bg-vox-success animate-pulse" :
            ws.status === "connecting" ? "bg-vox-warning animate-pulse" :
            ws.status === "error" ? "bg-vox-danger" : "bg-vox-text-muted"
          }`} />
          <div>
            <p className="text-sm font-semibold text-vox-text">
              {isActive ? "Live Analysis Active" : "Ready to Analyse"}
            </p>
            <p className="text-[10px] font-mono text-vox-text-muted">
              Session: {sessionId} • Status: {ws.status}
              {demoStreamingType && ` • Demo: ${demoStreamingType}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isActive ? (
            <button
              onClick={handleStartAnalysis}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-vox-cyan/20 to-vox-purple/20
                text-vox-cyan font-semibold text-sm border border-vox-cyan/30
                hover:from-vox-cyan/30 hover:to-vox-purple/30 hover:shadow-glow-cyan
                transition-all duration-200 flex items-center gap-2"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                <circle cx="12" cy="12" r="3" />
                <path d="M8.1 15.9a6 6 0 010-7.8M15.9 8.1a6 6 0 010 7.8" />
              </svg>
              Start Analysis
            </button>
          ) : (
            <button
              onClick={handleStopAnalysis}
              className="px-6 py-2.5 rounded-xl bg-vox-danger/20 text-vox-danger font-semibold text-sm
                border border-vox-danger/30 hover:bg-vox-danger/30 transition-all duration-200
                flex items-center gap-2"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Main Analysis Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Waveform — takes 2 columns */}
        <div className="lg:col-span-2">
          <WaveformVisualizer
            analyserNode={audio.analyserNode}
            isActive={isActive}
            isThreat={isThreat}
            height={220}
          />

          {/* Real-time metrics bar */}
          {latestResult && (
            <div className="mt-3 glass-subtle rounded-xl px-4 py-2.5 flex flex-wrap items-center gap-6 text-xs font-mono text-vox-text-dim animate-[fade-in_0.2s]">
              <span>
                Flatness: <span className={latestResult.spectral_flatness && latestResult.spectral_flatness > 0.35 ? "text-vox-danger" : "text-vox-success"}>
                  {latestResult.spectral_flatness?.toFixed(4) ?? "—"}
                </span>
              </span>
              <span>
                Centroid: <span className="text-vox-cyan">{latestResult.spectral_centroid_hz?.toFixed(0) ?? "—"} Hz</span>
              </span>
              <span>
                HF Ratio: <span className={latestResult.hf_energy_ratio && (latestResult.hf_energy_ratio < 0.01 || latestResult.hf_energy_ratio > 0.7) ? "text-vox-danger" : "text-vox-success"}>
                  {latestResult.hf_energy_ratio?.toFixed(4) ?? "—"}
                </span>
              </span>
              <span>
                Latency: <span className={latestResult.latency_ms < 200 ? "text-vox-success" : "text-vox-danger"}>
                  {latestResult.latency_ms.toFixed(0)}ms
                </span>
              </span>
            </div>
          )}
        </div>

        {/* Right column: Gauge + Demo Presets */}
        <div className="space-y-4">
          <ConfidenceGauge
            confidence={latestResult?.confidence ?? 0}
            verdict={latestResult?.verdict ?? "human"}
          />
          <DemoPresets
            onLoadPreset={handleDemoPreset}
            isStreaming={isActive}
          />
        </div>
      </div>

      {/* Audio Error */}
      {audio.error && (
        <div className="glass rounded-xl p-4 neon-border-danger animate-[slide-up_0.3s]">
          <p className="text-sm text-vox-danger font-medium">⚠ Audio Error</p>
          <p className="text-xs text-vox-text-dim mt-1">{audio.error}</p>
        </div>
      )}

      {/* Voice CAPTCHA Modal */}
      <ChallengeModal
        isOpen={challengePhrase !== null}
        phrase={challengePhrase || ""}
        onSubmit={(transcript) => {
          ws.sendChallengeResponse(transcript);
        }}
        onCancel={() => setChallengePhrase(null)}
      />

      {/* Challenge Result Toast */}
      {challengeResult && (
        <div className={`fixed bottom-6 right-6 z-50 glass rounded-xl p-4 animate-[slide-up_0.3s] ${
          challengeResult.matched ? "neon-border-cyan" : "neon-border-danger"
        }`}>
          <p className={`text-sm font-semibold ${challengeResult.matched ? "text-vox-success" : "text-vox-danger"}`}>
            {challengeResult.matched ? "✓ Challenge Passed" : "✗ Challenge Failed"}
          </p>
          <p className="text-xs text-vox-text-dim mt-1">
            Similarity: {(challengeResult.score * 100).toFixed(1)}%
          </p>
        </div>
      )}
    </div>
  );
}
