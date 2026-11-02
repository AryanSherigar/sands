import { useRef } from "react";
import { useEscapeKey } from "@/shared/hooks/useEscapeKey";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { describeEnding, describeEndingInput } from "../../../lib/endingText";
import type { EndingState } from "../../../types/simulation.types";

export interface StrategyEndingDialogProps {
  ending: EndingState;
  isOpen: boolean;
  onReviewRealm: () => void;
  onLeave: () => void;
}

const PERCENT_MAX = 100;
const KIND_LABELS: Record<string, string> = {
  victory: "Victory",
  defeat: "Defeat",
  graded: "Your reign is judged",
};

function InputBar({ label, value }: { label: string; value: number }) {
  const percent = Math.max(0, Math.min(PERCENT_MAX, value));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-[12px] text-[#42474b]">
        <span>{label}</span>
        <span className="font-semibold tabular-nums text-[#221A12]">{percent}</span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={PERCENT_MAX}
        aria-valuenow={percent}
        className="relative h-1.5 overflow-hidden rounded-full bg-[#ebdcb9]"
      >
        <div
          className="absolute inset-0 origin-left bg-[#46606E] transition-transform duration-700 ease-out"
          style={{ transform: `scaleX(${percent / PERCENT_MAX})` }}
        />
      </div>
    </div>
  );
}

export function StrategyEndingDialog({
  ending,
  isOpen,
  onReviewRealm,
  onLeave,
}: StrategyEndingDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, isOpen);
  useEscapeKey(isOpen, onReviewRealm);
  if (!isOpen) return null;

  const description = describeEnding(ending);
  const inputs = Object.entries(ending.inputs ?? {});

  return (
    <div className="strategy-surface fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#382f26]/60 p-4 backdrop-blur-sm">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ending-headline"
        className="strategy-rise flex w-full max-w-lg flex-col gap-5 rounded-2xl border-2 border-[#D2A94A]/60 bg-[#F7F0DC] p-6 text-[#221A12] shadow-2xl"
      >
        <header className="flex flex-col gap-1 text-center">
          <span className="text-[12px] text-[#785a00]">
            {`${KIND_LABELS[ending.kind] ?? "The campaign ends"} · Turn ${ending.turn}`}
          </span>
          <h2 id="ending-headline" className="font-serif text-[28px] font-bold">
            {description.headline}
          </h2>
          {description.gradeLabel ? (
            <p className="font-serif text-[18px] italic text-[#2e4856]">{description.gradeLabel}</p>
          ) : null}
          {description.summary ? (
            <p className="mt-1 text-[13px] text-[#42474b]">{description.summary}</p>
          ) : null}
        </header>

        {inputs.length > 0 ? (
          <section aria-label="How your reign was weighed" className="strategy-stagger flex flex-col gap-3">
            {inputs.map(([key, value]) => (
              <InputBar key={key} label={describeEndingInput(key)} value={value} />
            ))}
          </section>
        ) : null}

        <footer className="flex justify-end gap-2 border-t border-[#D2A94A]/30 pt-3">
          <button
            type="button"
            onClick={onReviewRealm}
            className="cursor-pointer rounded-xl border border-[#3A3128]/20 bg-[#fff8f4] px-4 py-2 text-[13px] font-semibold hover:bg-[#fbebde]"
          >
            Look over the realm
          </button>
          <button
            type="button"
            onClick={onLeave}
            className="cursor-pointer rounded-xl bg-[#2e4856] px-4 py-2 text-[13px] font-bold text-white hover:bg-[#46606E]"
          >
            Leave the campaign
          </button>
        </footer>
      </div>
    </div>
  );
}
