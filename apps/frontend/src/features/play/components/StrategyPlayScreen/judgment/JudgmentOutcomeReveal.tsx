import type { JudgmentOutcomeRevealProps } from "./StrategyJudgmentDialog.types";

export function JudgmentOutcomeReveal({ lines, onContinue }: JudgmentOutcomeRevealProps) {
  return (
    <div className="mx-auto flex max-w-[680px] flex-col items-center gap-6 rounded-lg border-2 border-[#D2A94A]/60 bg-[#F7F0DC] p-8 text-center shadow-2xl">
      <div
        data-testid="judgment-seal"
        aria-hidden="true"
        className="flex h-16 w-16 items-center justify-center rounded-full bg-[#9b3f35] text-white motion-safe:animate-pulse"
      >
        <span className="material-symbols-outlined text-[32px]">balance</span>
      </div>
      <h2 className="font-serif text-[28px] text-[#221A12]">Judgment is sealed</h2>
      <ul className="flex w-full flex-col gap-2 text-left">
        {lines.map((line) => (
          <li
            key={line}
            className="rounded border border-[#3A3128]/10 bg-[#fff1e6] px-4 py-2 text-[14px] text-[#221A12]"
          >
            {line}
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onContinue}
        className="rounded border border-[#a68028] bg-[#D2A94A] px-6 py-2.5 font-serif text-[16px] font-semibold text-[#221A12] hover:bg-[#c49b3d]"
      >
        Return to the realm
      </button>
    </div>
  );
}
