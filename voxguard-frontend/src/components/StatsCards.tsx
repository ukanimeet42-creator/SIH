"use client";

interface StatsCardsProps {
  activeSessions: number;
  threatsBlocked: number;
  avgLatency: number;
  chunksAnalysed: number;
}

interface StatCardData {
  label: string;
  value: string;
  unit: string;
  icon: React.ReactNode;
  color: string;
  glowClass: string;
}

export default function StatsCards({
  activeSessions,
  threatsBlocked,
  avgLatency,
  chunksAnalysed,
}: StatsCardsProps) {
  const stats: StatCardData[] = [
    {
      label: "Active Sessions",
      value: activeSessions.toString(),
      unit: "live",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
          <circle cx="12" cy="12" r="3" />
          <path d="M8.1 15.9a6 6 0 010-7.8M15.9 8.1a6 6 0 010 7.8" />
        </svg>
      ),
      color: "text-vox-cyan",
      glowClass: "neon-border-cyan",
    },
    {
      label: "Threats Blocked",
      value: threatsBlocked.toString(),
      unit: "detected",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
          <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" />
          <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
        </svg>
      ),
      color: threatsBlocked > 0 ? "text-vox-danger" : "text-vox-success",
      glowClass: threatsBlocked > 0 ? "neon-border-danger" : "neon-border-cyan",
    },
    {
      label: "Avg Latency",
      value: avgLatency.toFixed(0),
      unit: "ms",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" strokeLinecap="round" />
        </svg>
      ),
      color: avgLatency < 100 ? "text-vox-success" : avgLatency < 200 ? "text-vox-warning" : "text-vox-danger",
      glowClass: "neon-border-purple",
    },
    {
      label: "Chunks Analysed",
      value: chunksAnalysed > 999 ? `${(chunksAnalysed / 1000).toFixed(1)}k` : chunksAnalysed.toString(),
      unit: "total",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
          <path d="M18 20V10M12 20V4M6 20v-6" strokeLinecap="round" />
        </svg>
      ),
      color: "text-vox-purple",
      glowClass: "neon-border-purple",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <div
          key={stat.label}
          className={`glass rounded-2xl p-5 ${stat.glowClass} transition-all duration-300 hover:scale-[1.02] cursor-default`}
          style={{ animationDelay: `${i * 100}ms` }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className={`${stat.color} opacity-60`}>{stat.icon}</span>
            <span className="text-[10px] font-mono text-vox-text-muted uppercase tracking-wider">
              {stat.unit}
            </span>
          </div>
          <div className={`text-3xl font-bold font-mono ${stat.color} mb-1`}>
            {stat.value}
          </div>
          <div className="text-xs text-vox-text-dim">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
