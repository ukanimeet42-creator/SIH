"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import StatsCards from "@/components/StatsCards";
import LiveAnalysis from "@/components/LiveAnalysis";
import ThreatLog from "@/components/ThreatLog";
import { DetectionResult } from "@/hooks/useWebSocket";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [results, setResults] = useState<DetectionResult[]>([]);
  const [stats, setStats] = useState({
    activeSessions: 0,
    threatsBlocked: 0,
    avgLatency: 0,
    chunksAnalysed: 0,
  });

  // Fetch telemetry stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/telemetry/stats`);
      if (res.ok) {
        const data = await res.json();
        if (data.stats) {
          setStats({
            activeSessions: data.stats.active_sessions || 0,
            threatsBlocked: data.stats.threats_blocked || 0,
            avgLatency: data.stats.avg_latency_ms || 0,
            chunksAnalysed: data.stats.total_chunks_analysed || 0,
          });
        }
      }
    } catch {
      // Backend not running — use local state
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // Update stats from live results
  const handleResult = useCallback((result: DetectionResult) => {
    setResults((prev) => [...prev.slice(-199), result]);
    setStats((prev) => ({
      ...prev,
      chunksAnalysed: prev.chunksAnalysed + 1,
      threatsBlocked: prev.threatsBlocked + (result.is_synthetic ? 1 : 0),
      avgLatency:
        prev.chunksAnalysed === 0
          ? result.latency_ms
          : (prev.avgLatency * prev.chunksAnalysed + result.latency_ms) / (prev.chunksAnalysed + 1),
      activeSessions: Math.max(prev.activeSessions, 1),
    }));
  }, []);

  return (
    <div className="flex min-h-screen">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="flex-1 ml-[240px] p-8">
        {/* Top Bar */}
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-vox-text tracking-tight flex items-center gap-3">
              <span className="text-vox-cyan">◆</span>
              {activeTab === "dashboard" && "VoxGuard Dashboard"}
              {activeTab === "live" && "Live Analysis"}
              {activeTab === "threats" && "Threat Logs"}
              {activeTab === "reports" && "Reports"}
              {activeTab === "settings" && "Settings"}
            </h1>
            <p className="text-sm text-vox-text-muted mt-1">
              Real-time voice cloning detection & active prevention
            </p>
          </div>

          {/* Connection Status */}
          <div className="glass-subtle rounded-xl px-4 py-2 flex items-center gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-vox-success animate-pulse" />
              <span className="text-vox-text-dim font-mono">ENGINE ONLINE</span>
            </div>
            <div className="w-px h-4 bg-vox-border/30" />
            <span className="text-vox-text-muted font-mono">
              DSP MODE
            </span>
          </div>
        </header>

        {/* Dashboard View */}
        {activeTab === "dashboard" && (
          <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
            <StatsCards
              activeSessions={stats.activeSessions}
              threatsBlocked={stats.threatsBlocked}
              avgLatency={stats.avgLatency}
              chunksAnalysed={stats.chunksAnalysed}
            />

            <LiveAnalysis onResult={handleResult} />

            <ThreatLog results={results} />
          </div>
        )}

        {/* Live Analysis View */}
        {activeTab === "live" && (
          <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
            <LiveAnalysis onResult={handleResult} />
          </div>
        )}

        {/* Threat Logs View */}
        {activeTab === "threats" && (
          <div className="space-y-6 animate-[fade-in_0.3s_ease-out]">
            <ThreatLog results={results} />

            {results.length === 0 && (
              <div className="glass rounded-2xl p-12 neon-border-cyan flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-vox-cyan/10 flex items-center justify-center mb-4 border border-vox-cyan/20">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="w-8 h-8 text-vox-cyan/50">
                    <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" />
                    <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-vox-text mb-2">No Threat Events</h3>
                <p className="text-sm text-vox-text-muted max-w-sm">
                  Start a live analysis session to begin monitoring for voice cloning attempts.
                  Detection events will appear here in real time.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Reports View */}
        {activeTab === "reports" && (
          <div className="animate-[fade-in_0.3s_ease-out]">
            <div className="glass rounded-2xl p-8 neon-border-purple">
              <h3 className="text-lg font-semibold text-vox-text mb-4">Detection Summary</h3>
              <div className="grid grid-cols-2 gap-6">
                <div className="glass-subtle rounded-xl p-5">
                  <div className="text-xs text-vox-text-muted uppercase tracking-wider mb-2">Total Events</div>
                  <div className="text-3xl font-bold font-mono text-vox-cyan">{results.length}</div>
                </div>
                <div className="glass-subtle rounded-xl p-5">
                  <div className="text-xs text-vox-text-muted uppercase tracking-wider mb-2">Synthetic Detected</div>
                  <div className="text-3xl font-bold font-mono text-vox-danger">
                    {results.filter((r) => r.is_synthetic).length}
                  </div>
                </div>
                <div className="glass-subtle rounded-xl p-5">
                  <div className="text-xs text-vox-text-muted uppercase tracking-wider mb-2">Human Verified</div>
                  <div className="text-3xl font-bold font-mono text-vox-success">
                    {results.filter((r) => r.verdict === "human").length}
                  </div>
                </div>
                <div className="glass-subtle rounded-xl p-5">
                  <div className="text-xs text-vox-text-muted uppercase tracking-wider mb-2">Avg Confidence</div>
                  <div className="text-3xl font-bold font-mono text-vox-purple">
                    {results.length > 0
                      ? ((1 - results.reduce((a, r) => a + r.confidence, 0) / results.length) * 100).toFixed(1)
                      : "—"}
                    <span className="text-lg">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings View */}
        {activeTab === "settings" && (
          <div className="animate-[fade-in_0.3s_ease-out]">
            <div className="glass rounded-2xl p-8 neon-border-purple max-w-2xl">
              <h3 className="text-lg font-semibold text-vox-text mb-6">Engine Configuration</h3>

              <div className="space-y-5">
                {[
                  { label: "Detection Threshold", value: "0.85", desc: "Confidence above this marks audio as synthetic" },
                  { label: "Sample Rate", value: "16,000 Hz", desc: "Target audio sample rate (mono)" },
                  { label: "Sliding Window", value: "1.5s / 0.5s hop", desc: "Analysis window duration and stride" },
                  { label: "Inference Mode", value: "DSP Heuristic", desc: "Deterministic spectral analysis (no GPU required)" },
                  { label: "Challenge Verification", value: "Web Speech API", desc: "Browser-side STT for Voice CAPTCHA" },
                  { label: "Privacy Mode", value: "Zero Retention + PII Masking", desc: "Audio stays in RAM only, session IDs are SHA-256 hashed" },
                ].map((setting) => (
                  <div key={setting.label} className="flex items-center justify-between py-3 border-b border-vox-border/20 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-vox-text">{setting.label}</p>
                      <p className="text-xs text-vox-text-muted mt-0.5">{setting.desc}</p>
                    </div>
                    <span className="text-sm font-mono text-vox-cyan bg-vox-cyan/10 px-3 py-1 rounded-lg border border-vox-cyan/20">
                      {setting.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
