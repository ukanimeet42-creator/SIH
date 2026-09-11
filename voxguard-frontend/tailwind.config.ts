import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vox: {
          void: "#0a0a0f",
          surface: "#12141a",
          "surface-light": "#1a1d26",
          border: "#2a2d3a",
          cyan: "#00f0ff",
          "cyan-dim": "#00a3ad",
          purple: "#8b5cf6",
          "purple-dim": "#6d3fd4",
          danger: "#ef4444",
          "danger-dim": "#dc2626",
          success: "#22c55e",
          "success-dim": "#16a34a",
          warning: "#f59e0b",
          text: "#e2e8f0",
          "text-dim": "#94a3b8",
          "text-muted": "#64748b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        "glow-cyan": "0 0 20px rgba(0, 240, 255, 0.15), 0 0 60px rgba(0, 240, 255, 0.05)",
        "glow-purple": "0 0 20px rgba(139, 92, 246, 0.15), 0 0 60px rgba(139, 92, 246, 0.05)",
        "glow-danger": "0 0 20px rgba(239, 68, 68, 0.2), 0 0 60px rgba(239, 68, 68, 0.08)",
        "glow-success": "0 0 20px rgba(34, 197, 94, 0.15)",
        glass: "0 8px 32px rgba(0, 0, 0, 0.3)",
      },
      backdropBlur: {
        glass: "16px",
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "scan-line": "scan-line 3s linear infinite",
        "waveform-flow": "waveform-flow 1.5s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.4s ease-out",
        "border-glow": "border-glow 3s ease-in-out infinite",
        "threat-pulse": "threat-pulse 1s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "waveform-flow": {
          "0%, 100%": { transform: "scaleY(0.3)" },
          "50%": { transform: "scaleY(1)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "border-glow": {
          "0%, 100%": {
            borderColor: "rgba(0, 240, 255, 0.3)",
            boxShadow: "0 0 10px rgba(0, 240, 255, 0.1)",
          },
          "50%": {
            borderColor: "rgba(139, 92, 246, 0.5)",
            boxShadow: "0 0 20px rgba(139, 92, 246, 0.15)",
          },
        },
        "threat-pulse": {
          "0%, 100%": {
            boxShadow: "0 0 10px rgba(239, 68, 68, 0.2)",
          },
          "50%": {
            boxShadow: "0 0 30px rgba(239, 68, 68, 0.4), 0 0 60px rgba(239, 68, 68, 0.15)",
          },
        },
      },
    },
  },
  plugins: [],
};

export default config;
