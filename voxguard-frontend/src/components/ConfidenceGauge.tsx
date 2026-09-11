"use client";

import { useEffect, useRef } from "react";

interface ConfidenceGaugeProps {
  confidence: number; // 0-1 (synthetic probability)
  verdict: "human" | "synthetic" | "uncertain";
  size?: number;
}

export default function ConfidenceGauge({
  confidence,
  verdict,
  size = 180,
}: ConfidenceGaugeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animatedValueRef = useRef(0);
  const animFrameRef = useRef(0);

  const humanConfidence = Math.round((1 - confidence) * 100);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const radius = size / 2 - 16;
    const lineWidth = 10;
    const startAngle = Math.PI * 0.75;
    const endAngle = Math.PI * 2.25;
    const totalAngle = endAngle - startAngle;

    function animate() {
      // Smooth animation
      const target = 1 - confidence;
      animatedValueRef.current += (target - animatedValueRef.current) * 0.08;
      const val = animatedValueRef.current;

      ctx!.clearRect(0, 0, size, size);

      // Background arc track
      ctx!.beginPath();
      ctx!.arc(cx, cy, radius, startAngle, endAngle);
      ctx!.strokeStyle = "rgba(42, 45, 58, 0.5)";
      ctx!.lineWidth = lineWidth;
      ctx!.lineCap = "round";
      ctx!.stroke();

      // Value arc
      const valueAngle = startAngle + totalAngle * val;
      const arcGradient = ctx!.createConicGradient(startAngle, cx, cy);

      if (verdict === "human") {
        arcGradient.addColorStop(0, "#22c55e");
        arcGradient.addColorStop(0.5, "#00f0ff");
        arcGradient.addColorStop(1, "#22c55e");
      } else if (verdict === "synthetic") {
        arcGradient.addColorStop(0, "#ef4444");
        arcGradient.addColorStop(0.5, "#f59e0b");
        arcGradient.addColorStop(1, "#ef4444");
      } else {
        arcGradient.addColorStop(0, "#f59e0b");
        arcGradient.addColorStop(0.5, "#00f0ff");
        arcGradient.addColorStop(1, "#f59e0b");
      }

      ctx!.beginPath();
      ctx!.arc(cx, cy, radius, startAngle, valueAngle);
      ctx!.strokeStyle = arcGradient;
      ctx!.lineWidth = lineWidth;
      ctx!.lineCap = "round";
      ctx!.stroke();

      // Glow on the arc
      ctx!.save();
      ctx!.filter = "blur(6px)";
      ctx!.globalAlpha = 0.4;
      ctx!.beginPath();
      ctx!.arc(cx, cy, radius, startAngle, valueAngle);
      ctx!.strokeStyle = arcGradient;
      ctx!.lineWidth = lineWidth + 4;
      ctx!.lineCap = "round";
      ctx!.stroke();
      ctx!.restore();

      // Endpoint dot
      const dotX = cx + Math.cos(valueAngle) * radius;
      const dotY = cy + Math.sin(valueAngle) * radius;
      ctx!.beginPath();
      ctx!.arc(dotX, dotY, 5, 0, Math.PI * 2);
      ctx!.fillStyle = verdict === "human" ? "#22c55e" : verdict === "synthetic" ? "#ef4444" : "#f59e0b";
      ctx!.fill();

      // Glow on dot
      ctx!.save();
      ctx!.filter = "blur(8px)";
      ctx!.globalAlpha = 0.6;
      ctx!.beginPath();
      ctx!.arc(dotX, dotY, 8, 0, Math.PI * 2);
      ctx!.fillStyle = verdict === "human" ? "#22c55e" : verdict === "synthetic" ? "#ef4444" : "#f59e0b";
      ctx!.fill();
      ctx!.restore();

      animFrameRef.current = requestAnimationFrame(animate);
    }

    animFrameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [confidence, verdict, size]);

  const verdictColor =
    verdict === "human"
      ? "text-vox-success"
      : verdict === "synthetic"
      ? "text-vox-danger"
      : "text-vox-warning";

  const verdictLabel =
    verdict === "human" ? "Human" : verdict === "synthetic" ? "Synthetic" : "Uncertain";

  return (
    <div className="glass rounded-2xl p-6 flex flex-col items-center gap-2 neon-border-cyan">
      <div className="relative" style={{ width: size, height: size }}>
        <canvas
          ref={canvasRef}
          style={{ width: size, height: size }}
          className="block"
        />
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold font-mono ${verdictColor}`}>
            {humanConfidence}%
          </span>
          <span className="text-xs text-vox-text-muted mt-1">Human Confidence</span>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-1">
        <div
          className={`w-2 h-2 rounded-full ${
            verdict === "human"
              ? "bg-vox-success"
              : verdict === "synthetic"
              ? "bg-vox-danger animate-threat-pulse"
              : "bg-vox-warning"
          }`}
        />
        <span className={`text-sm font-semibold ${verdictColor}`}>{verdictLabel}</span>
      </div>
    </div>
  );
}
