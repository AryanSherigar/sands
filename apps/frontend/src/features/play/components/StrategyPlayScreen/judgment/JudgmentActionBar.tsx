import type { ChangeEvent, KeyboardEvent } from "react";
import {
  JUDGMENT_SPOKEN_MAX_CHARS,
  JUDGMENT_WHISPERS,
} from "../../../constants/judgment.constants";
import type { JudgmentActionBarProps } from "./StrategyJudgmentDialog.types";

const SPEECH_LABEL = "Speak to the court";

export function JudgmentActionBar({
  draftText,
  isBusy,
  canSpeak,
  onDraftChange,
  onSpeak,
  onWhisper,
}: JudgmentActionBarProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>): void =>
    onDraftChange(event.target.value);
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter") onSpeak();
  };

  return (
    <div className="fixed bottom-0 left-0 z-40 w-full border-t border-[#3A3128]/10 bg-[#F7F0DC]/95 px-8 py-2 shadow-[0_-6px_24px_rgba(58,49,40,0.12)] backdrop-blur-md">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-[#42474b]">
            Whispers
          </span>
          {JUDGMENT_WHISPERS.map((whisper) => (
            <button
              key={whisper}
              type="button"
              onClick={() => onWhisper(whisper)}
              className="max-w-sm shrink-0 truncate rounded-full border border-[#3A3128]/10 bg-[#f5e5d8]/70 px-3 py-1 text-left text-[12px] text-[#221A12] hover:bg-[#f0e0d2]"
            >
              {whisper}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <input
            type="text"
            aria-label={SPEECH_LABEL}
            value={draftText}
            maxLength={JUDGMENT_SPOKEN_MAX_CHARS}
            disabled={isBusy}
            placeholder="Speak to the court, or word your decree..."
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            className="flex-1 rounded-lg border border-[#3A3128]/15 bg-white/80 px-4 py-2 text-[14px] text-[#221A12] shadow-[inset_0_2px_4px_rgba(58,49,40,0.06)] focus:outline-none focus:ring-2 focus:ring-[#46606E]"
          />
          <button
            type="button"
            disabled={!canSpeak || isBusy || draftText.trim().length === 0}
            onClick={onSpeak}
            className="rounded-lg border border-[#2e4856] bg-[#46606E] px-5 py-2 text-[13px] font-bold text-white hover:bg-[#2e4856] disabled:opacity-50"
          >
            Speak
          </button>
        </div>
      </div>
    </div>
  );
}
