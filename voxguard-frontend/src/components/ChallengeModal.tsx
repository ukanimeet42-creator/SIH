"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface ChallengeModalProps {
  isOpen: boolean;
  phrase: string;
  onSubmit: (transcript: string) => void;
  onCancel: () => void;
}

export default function ChallengeModal({
  isOpen,
  phrase,
  onSubmit,
  onCancel,
}: ChallengeModalProps) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [timeLeft, setTimeLeft] = useState(15);
  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start Web Speech API recognition
  const startListening = useCallback(() => {
    setErrorMsg("");
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMsg("Speech API not available in your browser. Please type the phrase manually.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
        let finalTranscript = "";
        for (let i = 0; i < event.results.length; i++) {
          finalTranscript += event.results[i][0].transcript;
        }
        setTranscript(finalTranscript);
      };

      recognition.onerror = (event: any) => {
        console.error("[VoxGuard Challenge] Speech recognition error:", event.error);
        if (event.error === 'not-allowed') {
          setErrorMsg("Microphone access denied. Please allow microphone permissions or type the phrase manually.");
        } else {
          setErrorMsg(`Microphone error: ${event.error}. You can type manually instead.`);
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
      setIsListening(true);
    } catch (e: any) {
      console.error("Failed to start speech recognition", e);
      setErrorMsg("Could not start microphone. You can type the phrase manually instead.");
      setIsListening(false);
    }
  }, []);

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    setTimeLeft(15);
    setTranscript("");
    setErrorMsg("");

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
    };
  }, [isOpen]);

  const handleSubmit = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
    onSubmit(transcript);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-[fade-in_0.2s_ease-out]">
      <div className="glass rounded-3xl p-8 max-w-lg w-full mx-4 gradient-border animate-[slide-up_0.3s_ease-out]">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-vox-danger/20 flex items-center justify-center border border-vox-danger/30">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5 text-vox-danger">
              <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" />
              <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-vox-text">Voice CAPTCHA Challenge</h2>
            <p className="text-xs text-vox-text-muted">Synthetic voice detected — please verify your identity</p>
          </div>
        </div>

        {/* Challenge Phrase */}
        <div className="glass-subtle rounded-xl p-5 mb-6 border border-vox-cyan/20">
          <p className="text-[10px] uppercase tracking-widest text-vox-text-muted mb-2">Read this phrase aloud (or type it):</p>
          <p className="text-xl font-semibold text-vox-cyan font-mono leading-relaxed">
            &ldquo;{phrase}&rdquo;
          </p>
        </div>

        {/* Timer */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isListening ? "bg-vox-danger animate-pulse" : "bg-vox-text-muted"}`} />
            <span className="text-xs text-vox-text-dim">
              {isListening ? "Listening..." : "Press record or type response"}
            </span>
          </div>
          <span className={`text-sm font-mono font-bold ${timeLeft <= 5 ? "text-vox-danger" : "text-vox-text-dim"}`}>
            {timeLeft}s
          </span>
        </div>

        {/* Timer bar */}
        <div className="w-full h-1 rounded-full bg-vox-border/30 mb-5 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-vox-cyan to-vox-purple transition-all duration-1000 ease-linear"
            style={{ width: `${(timeLeft / 15) * 100}%` }}
          />
        </div>

        {/* Error Message */}
        {errorMsg && (
          <div className="p-3 mb-4 rounded-lg bg-vox-danger/10 border border-vox-danger/30 text-xs text-vox-danger">
            {errorMsg}
          </div>
        )}

        {/* Transcript / Manual Input */}
        <div className="glass-subtle rounded-xl p-1 mb-5 border border-vox-border/20">
          <input
            type="text"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Type your response here if mic fails..."
            disabled={isListening}
            className="w-full bg-transparent border-none outline-none text-sm text-vox-text font-mono p-3 placeholder:text-vox-text-dim/50"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {!isListening && (
            <button
              onClick={startListening}
              className="flex-1 py-3 rounded-xl bg-vox-cyan/20 text-vox-cyan font-semibold text-sm border border-vox-cyan/30 hover:bg-vox-cyan/30 transition-all"
            >
              🎤 Start Recording
            </button>
          )}
          {transcript.trim().length > 0 && !isListening && (
            <button
              onClick={handleSubmit}
              className="flex-1 py-3 rounded-xl bg-vox-success/20 text-vox-success font-semibold text-sm border border-vox-success/30 hover:bg-vox-success/30 transition-all"
            >
              ✓ Submit Response
            </button>
          )}
          <button
            onClick={onCancel}
            className="px-6 py-3 rounded-xl text-vox-text-muted text-sm border border-vox-border/30 hover:bg-white/[0.03] transition-all"
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
}
