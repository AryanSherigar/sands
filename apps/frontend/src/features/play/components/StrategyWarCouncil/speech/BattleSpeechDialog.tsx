import { useRef, useState } from "react";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { MAX_SPEECH_CHARS } from "../../../constants/strategy.constants";
import type { SpeechReception } from "../../../types/simulation.types";

export interface BattleSpeechDialogProps {
  isSending: boolean;
  reception: SpeechReception | null;
  reactionLine?: string | null;
  errorMessage: string | null;
  onSpeak: (speechText: string) => void;
  onSkip: () => void;
  onFinish: () => void;
}

const RECEPTION_LINES: Record<SpeechReception, string> = {
  stirred: "The ranks roar their answer. Spears beat on shields.",
  steady: "The ranks listen in silence, then nod.",
  cold: "A cold silence. Some men look at their boots.",
};

export function BattleSpeechDialog({
  isSending,
  reception,
  reactionLine = null,
  errorMessage,
  onSpeak,
  onSkip,
  onFinish,
}: BattleSpeechDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState("");
  const trimmed = text.trim();
  const hasSpoken = reception !== null;
  useFocusTrap(panelRef, true);
  useEscapeKey(!isSending, hasSpoken ? onFinish : onSkip);

  return (
    <div className="strategy-surface fixed inset-0 z-50 flex items-center justify-center bg-[#382f26]/60 p-4 backdrop-blur-sm">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Address your host"
        className="strategy-rise flex w-full max-w-lg flex-col gap-4 rounded-2xl border-2 border-[#D2A94A]/60 bg-[#F7F0DC] p-6 text-[#221A12] shadow-2xl"
      >
        <header className="flex flex-col gap-1">
          <h2 className="font-serif text-[24px] font-bold">Address your host</h2>
          <p className="text-[13px] text-[#42474b]">
            The ranks stand ready. Say what you would have them hear before the horns sound.
          </p>
        </header>

        {hasSpoken ? (
          <div className="flex flex-col gap-2">
            <p role="status" className="strategy-fade font-serif text-[18px] italic text-[#2e4856]">
              {RECEPTION_LINES[reception]}
            </p>
            {reactionLine ? (
              <p className="strategy-fade font-serif text-[15px] text-[#42474b]">{reactionLine}</p>
            ) : null}
          </div>
        ) : (
          <textarea
            aria-label="Your words to the host"
            value={text}
            maxLength={MAX_SPEECH_CHARS}
            rows={5}
            disabled={isSending}
            onChange={(event) => setText(event.target.value)}
            className="w-full resize-none rounded-lg border border-[#3A3128]/20 bg-[#fff8f4] p-3 text-[14px] disabled:opacity-60"
          />
        )}

        {errorMessage ? (
          <p role="alert" className="text-[12px] text-[#A8483E]">
            {errorMessage}
          </p>
        ) : null}

        <footer className="flex justify-end gap-2 border-t border-[#D2A94A]/30 pt-3">
          {hasSpoken ? (
            <button
              type="button"
              onClick={onFinish}
              className="cursor-pointer rounded-xl bg-[#2e4856] px-5 py-2 text-[13px] font-bold text-white hover:bg-[#46606E]"
            >
              To the field
            </button>
          ) : (
            <>
              <button
                type="button"
                disabled={isSending}
                onClick={onSkip}
                className="cursor-pointer rounded-xl border border-[#3A3128]/20 bg-[#fff8f4] px-4 py-2 text-[13px] font-semibold hover:bg-[#fbebde] disabled:opacity-50"
              >
                Say nothing
              </button>
              <button
                type="button"
                disabled={isSending || trimmed.length === 0}
                aria-busy={isSending}
                onClick={() => onSpeak(trimmed)}
                className="cursor-pointer rounded-xl bg-[#7c2820] px-5 py-2 text-[13px] font-bold text-white hover:bg-[#9b3f35] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSending ? "The ranks listen…" : "Address the host"}
              </button>
            </>
          )}
        </footer>
      </div>
    </div>
  );
}
