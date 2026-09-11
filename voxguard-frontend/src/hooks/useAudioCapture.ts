"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseAudioCaptureOptions {
  targetSampleRate?: number;
  bufferSize?: number;
  onAudioData?: (pcmBuffer: ArrayBuffer) => void;
}

export function useAudioCapture({
  targetSampleRate = 16000,
  bufferSize = 4096,
  onAudioData,
}: UseAudioCaptureOptions = {}) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceSampleRate, setDeviceSampleRate] = useState<number>(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  const startCapture = useCallback(async () => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Create AudioContext
      const ctx = new AudioContext({ sampleRate: targetSampleRate });
      audioContextRef.current = ctx;
      setDeviceSampleRate(ctx.sampleRate);

      // Create analyser for waveform visualisation
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;

      // Create source from microphone
      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;

      // Register and create AudioWorklet for 16kHz Int16 PCM conversion
      const workletCode = `
        class VoxGuardProcessor extends AudioWorkletProcessor {
          constructor() {
            super();
            this._buffer = [];
            this._bufferSize = ${bufferSize};
          }

          process(inputs) {
            const input = inputs[0];
            if (!input || !input[0]) return true;

            const channelData = input[0]; // Mono channel (already 16kHz from AudioContext)

            // Convert Float32 to Int16 PCM
            for (let i = 0; i < channelData.length; i++) {
              const s = Math.max(-1, Math.min(1, channelData[i]));
              this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7FFF);
            }

            // Send buffer when full
            if (this._buffer.length >= this._bufferSize) {
              const int16Array = new Int16Array(this._buffer.splice(0, this._bufferSize));
              this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
            }

            return true;
          }
        }

        registerProcessor('voxguard-processor', VoxGuardProcessor);
      `;

      const blob = new Blob([workletCode], { type: "application/javascript" });
      const workletUrl = URL.createObjectURL(blob);

      await ctx.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);

      const workletNode = new AudioWorkletNode(ctx, "voxguard-processor");
      workletNodeRef.current = workletNode;

      // Handle PCM data from worklet
      workletNode.port.onmessage = (event: MessageEvent) => {
        if (event.data instanceof ArrayBuffer) {
          onAudioData?.(event.data);
        }
      };

      // Connect: source → analyser → worklet → destination (muted)
      source.connect(analyser);
      analyser.connect(workletNode);
      workletNode.connect(ctx.destination);

      // Mute playback to prevent feedback
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0;
      workletNode.disconnect();
      workletNode.connect(gainNode);
      gainNode.connect(ctx.destination);

      // Keep analyser connected for visualisation
      source.connect(analyser);
      analyser.connect(workletNode);

      setIsCapturing(true);
      console.log(`[VoxGuard Audio] Capture started — sampleRate: ${ctx.sampleRate}Hz`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start audio capture";
      setError(message);
      console.error("[VoxGuard Audio] Error:", err);
    }
  }, [targetSampleRate, bufferSize, onAudioData]);

  const stopCapture = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCapturing(false);
    console.log("[VoxGuard Audio] Capture stopped");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCapture();
    };
  }, [stopCapture]);

  return {
    isCapturing,
    error,
    deviceSampleRate,
    analyserNode: analyserRef.current,
    startCapture,
    stopCapture,
  };
}
