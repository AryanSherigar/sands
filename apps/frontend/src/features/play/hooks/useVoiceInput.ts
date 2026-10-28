import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeAudio } from "../api/voice.api";
import { isRateLimitError } from "@/shared/lib/rate-limit-error";
import {
  isVoiceInputSupported,
  MicRecorder,
  MicRecorderError,
} from "@/shared/lib/audio/mic-recorder";

export type VoiceInputStatus = "idle" | "recording" | "transcribing" | "error";

export interface UseVoiceInputResult {
  status: VoiceInputStatus;
  isSupported: boolean;
  errorMessage: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  cancelRecording: () => void;
}

const ERROR_MESSAGES: Record<MicRecorderError["reason"], string> = {
  "permission-denied":
    "Microphone access was denied — enable it in your browser settings.",
  "no-device": "No microphone is available.",
  "unsupported-browser": "Voice input isn't supported in this browser.",
  "recorder-error": "Recording failed. Try again.",
};

/** Owns the mic-capture -> transcribe state machine for one action drawer.
 * Scoped to a single open drawer instance, so this lives as local hook
 * state rather than in play.store.ts. Never calls onSubmit — the caller
 * decides what to do with the transcript (populate its own text state for
 * the player to review, never auto-submit). */
export function useVoiceInput(
  onTranscribed: (text: string) => void,
  playthroughId?: string,
): UseVoiceInputResult {
  const [status, setStatus] = useState<VoiceInputStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const recorderRef = useRef<MicRecorder | null>(null);
  const isSupported = isVoiceInputSupported();

  useEffect(() => {
    return () => {
      recorderRef.current?.cancel();
    };
  }, []);

  const startRecording = useCallback(async () => {
    setErrorMessage(null);
    const recorder = new MicRecorder();
    try {
      await recorder.start();
    } catch (err) {
      const reason = err instanceof MicRecorderError ? err.reason : "recorder-error";
      setErrorMessage(ERROR_MESSAGES[reason]);
      setStatus("error");
      return;
    }
    recorderRef.current = recorder;
    setStatus("recording");
  }, []);

  const stopRecording = useCallback(async () => {
    const recorder = recorderRef.current;
    if (!recorder) return;
    setStatus("transcribing");
    try {
      const blob = await recorder.stop();
      const transcript = await transcribeAudio(blob, playthroughId);
      onTranscribed(transcript);
      setStatus("idle");
    } catch (error) {
      setErrorMessage(
        isRateLimitError(error)
          ? error.message
          : "Couldn't transcribe that. Try again.",
      );
      setStatus("error");
    } finally {
      recorderRef.current = null;
    }
  }, [onTranscribed, playthroughId]);

  const cancelRecording = useCallback(() => {
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setStatus("idle");
  }, []);

  return { status, isSupported, errorMessage, startRecording, stopRecording, cancelRecording };
}
