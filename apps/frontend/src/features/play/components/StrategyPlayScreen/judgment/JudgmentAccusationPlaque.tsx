import type { JudgmentAccusationPlaqueProps } from "./StrategyJudgmentDialog.types";

export function JudgmentAccusationPlaque({ charge, subjectLabel }: JudgmentAccusationPlaqueProps) {
  return (
    <div className="flex flex-col justify-center rounded-lg border border-[#3A3128]/10 bg-[#F7F0DC]/85 p-2 shadow-sm">
      <span className="text-[11px] font-semibold uppercase tracking-widest text-[#42474b]">
        Imperial inquest
      </span>
      <p className="mt-1 font-serif text-[20px] font-semibold leading-tight text-[#221A12]">
        {subjectLabel}
      </p>
      <span className="mt-1 text-[12px] italic text-[#7c2820]">{charge}</span>
    </div>
  );
}
