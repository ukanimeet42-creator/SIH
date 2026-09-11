"use client";

import { DetectionResult } from "@/hooks/useWebSocket";

interface ThreatLogProps {
  results: DetectionResult[];
}

export default function ThreatLog({ results }: ThreatLogProps) {
  const sortedResults = [...results].reverse(); // Most recent first

  return (
    <div className="glass rounded-2xl neon-border-cyan overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-vox-border/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-vox-cyan">
            <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <h3 className="text-sm font-semibold text-vox-text">Detection Log</h3>
        </div>
        <span className="text-[10px] font-mono text-vox-text-muted">
          {results.length} events
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[360px] overflow-y-auto">
        {sortedResults.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-vox-text-muted">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="w-10 h-10 mb-3 opacity-30">
              <circle cx="12" cy="12" r="10" />
              <path d="M8 15h8M9 9h.01M15 9h.01" strokeLinecap="round" />
            </svg>
            <p className="text-sm">No detection events yet</p>
            <p className="text-xs mt-1">Start live analysis to see results</p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-vox-border/20">
                <th className="text-left py-2.5 px-4 text-vox-text-muted font-medium">Time</th>
                <th className="text-left py-2.5 px-4 text-vox-text-muted font-medium">Verdict</th>
                <th className="text-left py-2.5 px-4 text-vox-text-muted font-medium">Confidence</th>
                <th className="text-left py-2.5 px-4 text-vox-text-muted font-medium">Latency</th>
                <th className="text-left py-2.5 px-4 text-vox-text-muted font-medium">Anomalies</th>
              </tr>
            </thead>
            <tbody>
              {sortedResults.map((result, i) => {
                const verdictColor =
                  result.verdict === "human"
                    ? "text-vox-success"
                    : result.verdict === "synthetic"
                    ? "text-vox-danger"
                    : "text-vox-warning";

                const rowBg =
                  result.verdict === "synthetic"
                    ? "bg-red-500/[0.04] hover:bg-red-500/[0.08]"
                    : "hover:bg-white/[0.02]";

                const tsString = result.timestamp.endsWith('Z') ? result.timestamp : `${result.timestamp}Z`;
                const ts = new Date(tsString);
                const timeStr = ts.toLocaleTimeString("en-US", {
                  hour12: false,
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                });

                return (
                  <tr
                    key={`${result.timestamp}-${i}`}
                    className={`border-b border-vox-border/10 transition-colors ${rowBg}`}
                  >
                    <td className="py-2.5 px-4 font-mono text-vox-text-dim">{timeStr}</td>
                    <td className="py-2.5 px-4">
                      <span className={`flex items-center gap-1.5 ${verdictColor} font-semibold`}>
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            result.verdict === "human"
                              ? "bg-vox-success"
                              : result.verdict === "synthetic"
                              ? "bg-vox-danger"
                              : "bg-vox-warning"
                          }`}
                        />
                        {result.verdict.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-vox-border/30 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              result.confidence > 0.85
                                ? "bg-vox-danger"
                                : result.confidence > 0.5
                                ? "bg-vox-warning"
                                : "bg-vox-success"
                            }`}
                            style={{ width: `${result.confidence * 100}%` }}
                          />
                        </div>
                        <span className="font-mono text-vox-text-dim">
                          {(result.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-vox-text-dim">
                      {result.latency_ms.toFixed(0)}ms
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {result.anomaly_flags.length === 0 ? (
                          <span className="text-vox-text-muted">—</span>
                        ) : (
                          result.anomaly_flags.map((flag) => (
                            <span
                              key={flag}
                              className="px-1.5 py-0.5 rounded-md text-[10px] font-mono bg-red-500/10 text-vox-danger border border-red-500/20"
                            >
                              {flag.replace(/_/g, " ").replace("anomaly", "").replace("abnormal", "").trim()}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
