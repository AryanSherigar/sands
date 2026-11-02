import { JUDGMENT_STANCES } from "../../../constants/judgment.constants";
import type { JudgmentCourtCardProps } from "./StrategyJudgmentDialog.types";

const ACCUSED_LABEL = "Accused";

export function JudgmentCourtCard({ member, isAccused }: JudgmentCourtCardProps) {
  const stance = member.stance ? JUDGMENT_STANCES[member.stance] : null;
  const ringClass = isAccused ? "border-[#7c2820]/60" : "border-[#46606E]/60";
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[#3A3128]/10 bg-[#F7F0DC]/85 p-2 shadow-sm">
      <div
        aria-hidden="true"
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 bg-[#f5e5d8] font-serif text-[20px] text-[#221A12] ${ringClass}`}
      >
        {member.name.charAt(0)}
      </div>
      <div className="min-w-0 flex-1">
        <span className="block truncate font-serif text-[18px] font-semibold leading-none text-[#221A12]">
          {member.name}
        </span>
        <span className="mt-1 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-[#46606E]">
          {stance ? (
            <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
              {stance.icon}
            </span>
          ) : null}
          {isAccused ? ACCUSED_LABEL : stance?.label}
        </span>
        <span className="block truncate text-[12px] capitalize text-[#42474b]">{member.kind}</span>
      </div>
    </div>
  );
}
