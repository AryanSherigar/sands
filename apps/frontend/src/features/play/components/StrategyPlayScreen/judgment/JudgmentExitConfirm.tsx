import type { JudgmentExitConfirmProps } from "./StrategyJudgmentDialog.types";

export function JudgmentExitConfirm({ onStay, onLeave }: JudgmentExitConfirmProps) {
  return (
    <div
      role="alertdialog"
      aria-label="Leave the hall"
      className="flex items-center justify-between gap-4 border-b border-[#7c2820]/30 bg-[#ffdad5] px-8 py-2"
    >
      <p className="text-[13px] text-[#410001]">
        Leaving the hall imprisons the accused. The verdict is then taken as imprisonment.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onStay}
          className="rounded border border-[#2e4856] bg-[#46606E] px-3 py-1 text-[12px] font-bold text-white"
        >
          Stay
        </button>
        <button
          type="button"
          onClick={onLeave}
          className="rounded border border-[#7c2820] bg-[#9b3f35] px-3 py-1 text-[12px] font-bold text-white"
        >
          Leave the hall
        </button>
      </div>
    </div>
  );
}
