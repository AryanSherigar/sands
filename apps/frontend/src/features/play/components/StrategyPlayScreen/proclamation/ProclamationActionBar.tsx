import { useState, type FC, type FormEvent } from "react";
import { PROCLAMATION_ENACTING_LABEL } from "../../../constants/proclamation.constants";

export interface ProclamationActionBarProps {
  isStreaming?: boolean;
  isEnacting?: boolean;
  onAddressCouncil?: (speech: string) => void;
  onPronounce: (verdict: "fiat" | "compromise") => void;
}

const SPEECH_LABEL = "Address the council";

export const ProclamationActionBar: FC<ProclamationActionBarProps> = ({
  isStreaming = false,
  isEnacting = false,
  onAddressCouncil,
  onPronounce,
}) => {
  const [speech, setSpeech] = useState("");
  const isBusy = isStreaming || isEnacting;

  const handleSubmitSpeech = (event: FormEvent): void => {
    event.preventDefault();
    if (!speech.trim() || isBusy) return;
    onAddressCouncil?.(speech.trim());
    setSpeech("");
  };

  return (
    <aside className="fixed bottom-0 left-0 right-0 z-40 border-t border-on-surface/15 bg-parchment-panel/95 shadow-[0_-4px_24px_rgba(58,49,40,0.08)] backdrop-blur-lg">
      <div className="mx-auto flex h-20 max-w-[1360px] items-center justify-between gap-6 px-8">
        {onAddressCouncil ? (
          <form
            onSubmit={handleSubmitSpeech}
            className="flex max-w-2xl flex-1 items-center gap-1 rounded-xl bg-[#efe6ce] px-4 py-2 shadow-[inset_0_2px_4px_rgba(58,49,40,0.09)] focus-within:ring-2 focus-within:ring-primary-container-wilds focus-within:ring-offset-2 focus-within:ring-offset-parchment-panel"
          >
            <span className="material-symbols-outlined text-[20px] text-on-surface-variant" aria-hidden="true">
              record_voice_over
            </span>
            <input
              type="text"
              aria-label={SPEECH_LABEL}
              value={speech}
              disabled={isBusy}
              onChange={(event) => setSpeech(event.target.value)}
              placeholder="Address the council with royal command..."
              className="w-full border-0 bg-transparent px-2 py-1 text-[14px] text-on-surface placeholder:italic placeholder:text-on-surface-variant/60 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!speech.trim() || isBusy}
              className="flex items-center gap-1 rounded-lg bg-primary-container-wilds px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white shadow-sm transition-all hover:brightness-110 active:translate-y-0.5 disabled:opacity-40"
            >
              Speak
              <span className="material-symbols-outlined text-[15px]" aria-hidden="true">
                send
              </span>
            </button>
          </form>
        ) : (
          <div className="flex-1" />
        )}
        <div className="relative flex shrink-0 items-center gap-4">
          <button
            type="button"
            onClick={() => onPronounce("fiat")}
            disabled={isBusy}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-b from-[#536e7d] to-[#2e4856] px-5 py-2.5 text-left text-white shadow-[0_4px_12px_rgba(46,72,86,0.22)] transition-all hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-primary-container-wilds focus:ring-offset-2 active:translate-y-0.5 disabled:opacity-40"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-black/15">
              <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                gavel
              </span>
            </span>
            <span className="flex flex-col">
              <span className="font-serif text-[18px] font-semibold leading-tight">Rule by Fiat</span>
              <span className="text-[12px] leading-tight text-white/80">Enforce as written</span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => onPronounce("compromise")}
            disabled={isBusy}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-b from-[#e2bb5c] to-secondary-container px-5 py-2.5 text-left text-on-surface shadow-[0_4px_14px_rgba(210,169,74,0.28)] transition-all hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 active:translate-y-0.5 disabled:opacity-40"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-black/10">
              <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                handshake
              </span>
            </span>
            <span className="flex flex-col">
              <span className="font-serif text-[18px] font-bold leading-tight">Adopt Compromise</span>
              <span className="text-[12px] leading-tight text-on-surface-variant">Amended terms</span>
            </span>
          </button>
          {isEnacting ? (
            <div
              role="status"
              className="absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-xl bg-parchment-panel px-4 shadow-md"
            >
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-secondary border-t-transparent" />
              <span className="font-serif text-[18px] italic text-on-surface">
                {PROCLAMATION_ENACTING_LABEL}
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
};
