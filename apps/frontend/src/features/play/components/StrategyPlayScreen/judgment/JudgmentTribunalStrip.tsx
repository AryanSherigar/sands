import { JUDGMENT_NO_APPEAL_LABEL } from "../../../constants/judgment.constants";
import type { JudgmentTribunalStripProps } from "./StrategyJudgmentDialog.types";

export function JudgmentTribunalStrip({ turn, summary }: JudgmentTribunalStripProps) {
  return (
    <div className="flex w-full items-center justify-between border-b border-[#3A3128]/10 bg-[#F7F0DC]/75 px-8 py-1 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[#f5e5d8]/90 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-widest text-[#221A12]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#7c2820]" aria-hidden="true" />
          Sovereign tribunal
        </span>
        <span className="hidden text-[12px] italic text-[#42474b] md:inline">{summary}</span>
      </div>
      <div className="flex items-center gap-4 text-[12px] text-[#42474b]">
        <span>Turn {turn}</span>
        <span className="font-medium italic text-[#7c2820]">{JUDGMENT_NO_APPEAL_LABEL}</span>
      </div>
    </div>
  );
}
