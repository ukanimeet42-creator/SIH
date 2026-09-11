"use client";

import { useState } from "react";

interface DemoPresetsProps {
  onLoadPreset: (type: "authentic" | "synthetic", audioData: ArrayBuffer) => void;
  isStreaming: boolean;
}

/**
 * Generate a PCM Int16 buffer of authentic-sounding speech
 * with natural formants, vibrato, and aspiration noise.
 */
function generateAuthenticAudio(durationS: number = 3, sr: number = 16000): ArrayBuffer {
  const numSamples = Math.floor(sr * durationS);
  const buffer = new Int16Array(numSamples);

  for (let i = 0; i < numSamples; i++) {
    const t = i / sr;

    // Fundamental with vibrato
    const f0 = 140 + 6 * Math.sin(2 * Math.PI * 5 * t);
    let sample = 0;

    // Formants
    sample += 0.45 * Math.sin(2 * Math.PI * f0 * t);
    sample += 0.25 * Math.sin(2 * Math.PI * 720 * t);
    sample += 0.15 * Math.sin(2 * Math.PI * 1100 * t);
    sample += 0.06 * Math.sin(2 * Math.PI * 2500 * t);
    sample += 0.02 * Math.sin(2 * Math.PI * 3600 * t);

    // Natural envelope
    const env = (0.5 + 0.5 * Math.sin(2 * Math.PI * 3.0 * t)) *
                (0.7 + 0.3 * Math.sin(2 * Math.PI * 0.7 * t));
    sample *= env;

    // Aspiration noise
    sample += (Math.random() * 2 - 1) * 0.025;

    buffer[i] = Math.max(-32768, Math.min(32767, Math.round(sample * 24000)));
  }

  return buffer.buffer;
}

/**
 * Generate a PCM Int16 buffer that mimics vocoder-generated audio
 * with flat harmonics, low dynamic range, and phase artefacts.
 */
function generateSyntheticAudio(durationS: number = 3, sr: number = 16000): ArrayBuffer {
  const numSamples = Math.floor(sr * durationS);
  const buffer = new Int16Array(numSamples);

  for (let i = 0; i < numSamples; i++) {
    const t = i / sr;
    let sample = 0;

    // Vocoder frame artefact: phase jumps every 20ms
    const frameSize = Math.floor(0.02 * sr);
    const frameIdx = Math.floor(i / frameSize);
    const phaseOffset = (frameIdx * 2.5) % (2 * Math.PI);

    // Flat harmonics (unnatural, robotic)
    for (let h = 1; h <= 25; h++) {
      const freq = 160 * h;
      if (freq > sr / 2) break;
      // High frequencies get more amplitude to create a flat Mel spectrum and high ZCR
      const amp = 0.02 + (h * 0.003);
      sample += amp * Math.sin(2 * Math.PI * freq * t + phaseOffset);
    }

    // Inject high-frequency white noise to increase Spectral Flatness and ZCR
    const noise = (Math.random() * 2 - 1) * 0.45;
    sample += noise;

    // Extreme clipping / compression to trigger low dynamic range
    sample = Math.tanh(sample * 10) * 0.35;

    buffer[i] = Math.max(-32768, Math.min(32767, Math.round(sample * 24000)));
  }

  return buffer.buffer;
}


export default function DemoPresets({ onLoadPreset, isStreaming }: DemoPresetsProps) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [loadingPreset, setLoadingPreset] = useState<string | null>(null);

  const handleLoad = async (type: "authentic" | "synthetic", index: number) => {
    setLoadingPreset(`${type}-${index}`);

    // Generate audio (simulates loading)
    await new Promise((r) => setTimeout(r, 300));

    const audio = type === "authentic"
      ? generateAuthenticAudio(3 + index)
      : generateSyntheticAudio(3 + index);

    onLoadPreset(type, audio);
    setLoadingPreset(null);
  };

  return (
    <div className="glass rounded-2xl neon-border-purple overflow-hidden">
      {/* Toggle Header */}
      <div className="px-5 py-4 border-b border-vox-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-vox-purple">
            <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />
          </svg>
          <h3 className="text-sm font-semibold text-vox-text">Demo Presets</h3>
        </div>
        <button
          onClick={() => setIsEnabled(!isEnabled)}
          className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
            isEnabled ? "bg-vox-purple/30 border border-vox-purple/50" : "bg-vox-border/30 border border-vox-border/50"
          }`}
        >
          <span
            className={`absolute top-0.5 w-5 h-5 rounded-full transition-all duration-200 ${
              isEnabled
                ? "left-[22px] bg-vox-purple shadow-glow-purple"
                : "left-0.5 bg-vox-text-muted"
            }`}
          />
        </button>
      </div>

      {/* Presets Grid */}
      {isEnabled && (
        <div className="p-4 space-y-3 animate-[slide-up_0.2s_ease-out]">
          <p className="text-[10px] text-vox-text-muted uppercase tracking-widest mb-2">
            Load sample audio for demo
          </p>

          {/* Authentic Samples */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono text-vox-success">AUTHENTIC SAMPLES</span>
            <div className="grid grid-cols-2 gap-2">
              {[1, 2].map((idx) => (
                <button
                  key={`auth-${idx}`}
                  disabled={isStreaming || loadingPreset !== null}
                  onClick={() => handleLoad("authentic", idx)}
                  className="glass-subtle rounded-xl px-3 py-2.5 text-xs text-vox-text-dim
                    border border-vox-success/20 hover:border-vox-success/40 hover:bg-vox-success/5
                    transition-all disabled:opacity-40 disabled:cursor-not-allowed
                    flex items-center gap-2"
                >
                  <div className="w-6 h-6 rounded-lg bg-vox-success/10 flex items-center justify-center">
                    {loadingPreset === `authentic-${idx}` ? (
                      <span className="w-3 h-3 border-2 border-vox-success/50 border-t-vox-success rounded-full animate-spin" />
                    ) : (
                      <span className="text-vox-success text-[10px]">▶</span>
                    )}
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-vox-text text-[11px]">Human #{idx}</div>
                    <div className="text-[9px] text-vox-text-muted">{2 + idx}s speech</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Synthetic Samples */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono text-vox-danger">DEEPFAKE SAMPLES</span>
            <div className="grid grid-cols-2 gap-2">
              {[1, 2].map((idx) => (
                <button
                  key={`synth-${idx}`}
                  disabled={isStreaming || loadingPreset !== null}
                  onClick={() => handleLoad("synthetic", idx)}
                  className="glass-subtle rounded-xl px-3 py-2.5 text-xs text-vox-text-dim
                    border border-vox-danger/20 hover:border-vox-danger/40 hover:bg-vox-danger/5
                    transition-all disabled:opacity-40 disabled:cursor-not-allowed
                    flex items-center gap-2"
                >
                  <div className="w-6 h-6 rounded-lg bg-vox-danger/10 flex items-center justify-center">
                    {loadingPreset === `synthetic-${idx}` ? (
                      <span className="w-3 h-3 border-2 border-vox-danger/50 border-t-vox-danger rounded-full animate-spin" />
                    ) : (
                      <span className="text-vox-danger text-[10px]">▶</span>
                    )}
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-vox-text text-[11px]">Clone #{idx}</div>
                    <div className="text-[9px] text-vox-text-muted">{2 + idx}s vocoder</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
