"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface DetectionResult {
  is_synthetic: boolean;
  confidence: number;
  verdict: "human" | "synthetic" | "uncertain";
  anomaly_flags: string[];
  latency_ms: number;
  timestamp: string;
  spectral_flatness?: number;
  spectral_centroid_hz?: number;
  hf_energy_ratio?: number;
}

export interface StreamMessage {
  type: string;
  session_id: string;
  result?: DetectionResult;
  challenge?: string | null;
  error?: string | null;
}

export interface ChallengeResult {
  matched: boolean;
  similarity_score: number;
  expected_phrase: string;
  recognised_text: string;
}

interface UseWebSocketOptions {
  url: string;
  sessionId: string;
  onResult?: (result: DetectionResult) => void;
  onChallenge?: (phrase: string) => void;
  onChallengeResult?: (result: ChallengeResult) => void;
  onError?: (error: string) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function useWebSocket({
  url,
  sessionId,
  onResult,
  onChallenge,
  onChallengeResult,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [latestResult, setLatestResult] = useState<DetectionResult | null>(null);
  const [resultHistory, setResultHistory] = useState<DetectionResult[]>([]);

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    const fullUrl = `${url}/${sessionId}`;
    setStatus("connecting");

    try {
      const ws = new WebSocket(fullUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        console.log("[VoxGuard WS] Connected to", fullUrl);
      };

      ws.onmessage = (event) => {
        if (typeof event.data !== "string") return;

        try {
          const msg: StreamMessage = JSON.parse(event.data);

          switch (msg.type) {
            case "connected":
              console.log("[VoxGuard WS] Session initialised:", msg);
              break;

            case "detection_result":
              if (msg.result) {
                setLatestResult(msg.result);
                setResultHistory((prev) => [...prev.slice(-99), msg.result!]);
                onResult?.(msg.result);
              }
              if (msg.challenge) {
                onChallenge?.(msg.challenge);
              }
              break;

            case "challenge_result":
              onChallengeResult?.(msg as unknown as ChallengeResult);
              break;

            case "error":
              onError?.(msg.error || "Unknown error");
              break;

            case "pong":
              break;
          }
        } catch (e) {
          console.warn("[VoxGuard WS] Failed to parse message:", e);
        }
      };

      ws.onerror = (e) => {
        console.error("[VoxGuard WS] Error:", e);
        setStatus("error");
        onError?.("WebSocket connection error");
      };

      ws.onclose = (e) => {
        setStatus("disconnected");
        console.log("[VoxGuard WS] Closed:", e.code, e.reason);

        if (autoReconnect && e.code !== 1000) {
          reconnectTimerRef.current = setTimeout(() => {
            console.log("[VoxGuard WS] Reconnecting...");
            connect();
          }, reconnectInterval);
        }
      };
    } catch (e) {
      setStatus("error");
      console.error("[VoxGuard WS] Failed to create WebSocket:", e);
    }
  }, [url, sessionId, autoReconnect, reconnectInterval, onResult, onChallenge, onChallengeResult, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnected");
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  const sendAudio = useCallback((pcmData: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(pcmData);
    }
  }, []);

  const sendChallengeResponse = useCallback((transcript: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "challenge_response",
          transcript,
        })
      );
    }
  }, []);

  const clearHistory = useCallback(() => {
    setResultHistory([]);
    setLatestResult(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    latestResult,
    resultHistory,
    connect,
    disconnect,
    sendAudio,
    sendChallengeResponse,
    clearHistory,
  };
}
