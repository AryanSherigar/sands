import { useCallback, useState, type KeyboardEvent } from "react";
import { useVoiceInput, type VoiceInputStatus } from "../../../hooks/useVoiceInput";
import type { SpeechTalkInputProps } from "./SpeechTalkInput.types";

const PUSH_KEYS = new Set([" ", "Enter"]);
const SPEAK_LABELS: Record<VoiceInputStatus, string> = {
  idle: "Hold to speak",
  recording: "Listening… release to finish",
  transcribing: "Writing down your words…",
  error: "Hold to speak",
};

export function SpeechTalkInput({
  playthroughId,
  talkLabel,
  isSubmitting,
  onSubmit,
}: SpeechTalkInputProps) {
  const [text, setText] = useState("");
  const appendTranscript = useCallback(
    (transcript: string) => setText((current) => `${current} ${transcript}`.trim()),
    [],
  );
  const voice = useVoiceInput(appendTranscript, playthroughId);
  const canDeliver = text.trim().length > 0 && !isSubmitting && voice.status === "idle";

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (PUSH_KEYS.has(event.key) && !event.repeat) {
      event.preventDefault();
      void voice.startRecording();
    }
  };
  const handleRelease = () => void voice.stopRecording();
  const handleKeyUp = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (PUSH_KEYS.has(event.key)) handleRelease();
  };
  const handleDeliver = () => {
    onSubmit(text.trim());
    setText("");
  };

  return (
    <div className="space-y-3">
      <h3 className="font-semibold">{talkLabel}</h3>
      <label htmlFor="battle-speech-talk" className="sr-only">
        Your talk
      </label>
      <textarea
        id="battle-speech-talk"
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={4}
        placeholder="Speak to your army, or write what you would say."
        className="w-full rounded-md border border-[#3A3128]/30 bg-white/70 p-3 text-sm focus-visible:outline focus-visible:outline-2"
      />
      {voice.isSupported ? (
        <button
          type="button"
          disabled={isSubmitting || voice.status === "transcribing"}
          onPointerDown={() => void voice.startRecording()}
          onPointerUp={handleRelease}
          onPointerLeave={handleRelease}
          onPointerCancel={handleRelease}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          className="w-full rounded-md border border-[#46606E] px-4 py-2 hover:bg-[#E8DEC6] focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
        >
          {SPEAK_LABELS[voice.status]}
        </button>
      ) : (
        <p className="text-xs">Voice input isn&apos;t available in this browser. Type your talk instead.</p>
      )}
      {voice.errorMessage && (
        <p role="alert" className="text-sm text-[#A8483E]">
          {voice.errorMessage}
        </p>
      )}
      <button
        type="button"
        disabled={!canDeliver}
        onClick={handleDeliver}
        className="rounded-md bg-[#46606E] px-4 py-2 text-white hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
      >
        Deliver talk
      </button>
    </div>
  );
}
