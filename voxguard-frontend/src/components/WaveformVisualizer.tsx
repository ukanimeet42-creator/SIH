"use client";

import { useCallback, useEffect, useRef } from "react";

interface WaveformVisualizerProps {
  analyserNode: AnalyserNode | null;
  isActive: boolean;
  isThreat?: boolean;
  height?: number;
}

export default function WaveformVisualizer({
  analyserNode,
  isActive,
  isThreat = false,
  height = 200,
}: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;
    const centerY = h / 2;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Background glow
    const bgGrad = ctx.createRadialGradient(w / 2, centerY, 0, w / 2, centerY, w * 0.6);
    bgGrad.addColorStop(0, isThreat ? "rgba(239, 68, 68, 0.05)" : "rgba(0, 240, 255, 0.04)");
    bgGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // Center line
    ctx.strokeStyle = "rgba(42, 45, 58, 0.5)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 8]);
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(w, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    if (analyserNode && isActive) {
      const bufferLength = analyserNode.fftSize;
      const dataArray = new Float32Array(bufferLength);
      analyserNode.getFloatTimeDomainData(dataArray);

      // Main waveform
      const gradient = ctx.createLinearGradient(0, 0, w, 0);
      if (isThreat) {
        gradient.addColorStop(0, "rgba(239, 68, 68, 0.9)");
        gradient.addColorStop(0.5, "rgba(239, 68, 68, 1)");
        gradient.addColorStop(1, "rgba(245, 158, 11, 0.9)");
      } else {
        gradient.addColorStop(0, "rgba(0, 240, 255, 0.8)");
        gradient.addColorStop(0.5, "rgba(139, 92, 246, 0.9)");
        gradient.addColorStop(1, "rgba(0, 240, 255, 0.8)");
      }

      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";

      ctx.beginPath();
      const sliceWidth = w / bufferLength;

      for (let i = 0; i < bufferLength; i++) {
        const x = i * sliceWidth;
        const v = dataArray[i];
        const y = centerY + v * centerY * 0.85;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Glow effect
      ctx.globalAlpha = 0.3;
      ctx.lineWidth = 6;
      ctx.filter = "blur(4px)";
      ctx.strokeStyle = gradient;
      ctx.beginPath();
      for (let i = 0; i < bufferLength; i++) {
        const x = i * sliceWidth;
        const v = dataArray[i];
        const y = centerY + v * centerY * 0.85;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.filter = "none";
      ctx.globalAlpha = 1;

      // Filled area under waveform
      const fillGradient = ctx.createLinearGradient(0, centerY - h / 2, 0, centerY + h / 2);
      if (isThreat) {
        fillGradient.addColorStop(0, "rgba(239, 68, 68, 0.15)");
        fillGradient.addColorStop(0.5, "rgba(239, 68, 68, 0.03)");
        fillGradient.addColorStop(1, "rgba(239, 68, 68, 0.15)");
      } else {
        fillGradient.addColorStop(0, "rgba(0, 240, 255, 0.1)");
        fillGradient.addColorStop(0.5, "rgba(139, 92, 246, 0.02)");
        fillGradient.addColorStop(1, "rgba(0, 240, 255, 0.1)");
      }

      ctx.fillStyle = fillGradient;
      ctx.beginPath();
      for (let i = 0; i < bufferLength; i++) {
        const x = i * sliceWidth;
        const v = dataArray[i];
        const y = centerY + v * centerY * 0.85;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineTo(w, centerY);
      ctx.lineTo(0, centerY);
      ctx.closePath();
      ctx.fill();
    } else {
      // Idle animation — gentle sine wave
      const time = Date.now() / 1000;
      ctx.strokeStyle = "rgba(42, 45, 58, 0.6)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let x = 0; x < w; x++) {
        const y =
          centerY +
          Math.sin(x * 0.02 + time * 2) * 8 +
          Math.sin(x * 0.01 + time * 1.5) * 4;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    animationRef.current = requestAnimationFrame(draw);
  }, [analyserNode, isActive, isThreat]);

  useEffect(() => {
    animationRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animationRef.current);
  }, [draw]);

  return (
    <div
      className={`relative rounded-2xl overflow-hidden scan-overlay ${
        isThreat ? "neon-border-danger animate-threat-pulse" : "neon-border-cyan"
      }`}
    >
      <canvas
        ref={canvasRef}
        style={{ height }}
        className="w-full block"
      />

      {/* Status badge */}
      <div className="absolute top-3 left-3 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isActive ? (isThreat ? "bg-vox-danger" : "bg-vox-success") : "bg-vox-text-muted"} ${isActive ? "animate-pulse" : ""}`} />
        <span className="text-xs font-mono text-vox-text-dim">
          {isActive ? (isThreat ? "THREAT DETECTED" : "ANALYSING") : "IDLE"}
        </span>
      </div>

      {/* Frequency label */}
      <div className="absolute bottom-3 right-3">
        <span className="text-[10px] font-mono text-vox-text-muted/50">16kHz MONO PCM</span>
      </div>
    </div>
  );
}
