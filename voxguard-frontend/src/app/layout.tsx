import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxGuard Engine — Real-Time Voice Cloning Detection",
  description:
    "Real-time voice cloning detection and active prevention engine. Analyses live audio streams for synthetic voice artefacts using deterministic DSP heuristics and optional ONNX model inference.",
  keywords: [
    "voice cloning detection",
    "deepfake audio",
    "anti-spoofing",
    "voice security",
    "VoxGuard",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-vox-void text-vox-text antialiased bg-grid-pattern min-h-screen">
        {children}
      </body>
    </html>
  );
}
