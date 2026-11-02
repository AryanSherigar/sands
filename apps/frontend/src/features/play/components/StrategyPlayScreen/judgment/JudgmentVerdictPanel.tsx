import { JUDGMENT_VERDICTS } from "../../../constants/judgment.constants";
import { JudgmentNuanceChips } from "./JudgmentNuanceChips";
import type { JudgmentVerdictPanelProps } from "./StrategyJudgmentDialog.types";

const VERDICT_BASE =
  "flex flex-col items-start rounded border p-3 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#46606E] disabled:opacity-60";
const VERDICT_IDLE = "border-[#3A3128]/10 bg-[#fff1e6] text-[#221A12] hover:bg-[#f5e5d8]";
const VERDICT_ACTIVE = "border-[#2e4856] bg-[#46606E] text-white shadow-md";

export function JudgmentVerdictPanel({
  selectedVerdict,
  selectedNuance,
  isDisabled,
  onSelectVerdict,
  onSelectNuance,
  onPronounce,
}: JudgmentVerdictPanelProps) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-[#3A3128]/10 bg-[#F7F0DC]/85 p-4 shadow-[0_12px_36px_-6px_rgba(58,49,40,0.16)] backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-[#3A3128]/10 pb-1">
        <div>
          <span className="text-[11px] uppercase tracking-widest text-[#42474b]">
            Sovereign authority
          </span>
          <h2 className="font-serif text-[24px] leading-tight text-[#221A12]">Your judgment</h2>
        </div>
        <span className="rounded bg-[#fed16e]/40 px-2 py-1 text-[11px] font-semibold text-[#251a00]">
          Absolute
        </span>
      </div>
      <p className="text-[12px] leading-relaxed text-[#42474b]">
        The hall is hushed. No counselor may overrule the Sovereign's voice once spoken from the
        dais.
      </p>
      <div role="group" aria-label="Verdict" className="grid grid-cols-2 gap-2">
        {JUDGMENT_VERDICTS.map((verdict) => (
          <button
            key={verdict.id}
            type="button"
            aria-pressed={selectedVerdict === verdict.id}
            disabled={isDisabled}
            onClick={() => onSelectVerdict(verdict.id)}
            className={`${VERDICT_BASE} ${selectedVerdict === verdict.id ? VERDICT_ACTIVE : VERDICT_IDLE}`}
          >
            <span className="mb-1 flex w-full items-center justify-between">
              <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                {verdict.icon}
              </span>
              <span className="text-[12px] opacity-70">[{verdict.shortcut}]</span>
            </span>
            <span className="font-serif text-[18px] font-semibold">{verdict.label}</span>
            <span className="text-[11px] opacity-80">{verdict.tagline}</span>
          </button>
        ))}
      </div>
      <JudgmentNuanceChips
        verdict={selectedVerdict}
        selectedNuance={selectedNuance}
        onSelectNuance={onSelectNuance}
      />
      <button
        type="button"
        disabled={isDisabled}
        onClick={onPronounce}
        className="flex w-full items-center justify-center gap-2 rounded border border-[#a68028] bg-[#D2A94A] px-4 py-3 font-serif text-[18px] font-semibold text-[#221A12] shadow-[0_4px_16px_rgba(120,90,0,0.22)] transition-all hover:bg-[#c49b3d] active:translate-y-px focus:outline-none focus-visible:ring-2 focus-visible:ring-[#785a00] focus-visible:ring-offset-2 disabled:opacity-60"
      >
        Pronounce judgment
        <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
          balance
        </span>
      </button>
    </div>
  );
}
