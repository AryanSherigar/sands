import type { FC } from "react";
import type { StrategyLetterShelfPillProps } from "./StrategyLetterShelfPill.types";

export const StrategyLetterShelfPill: FC<StrategyLetterShelfPillProps> = ({
  dispatchNumber,
  onClick,
}) => (
  <button
    type="button"
    onClick={onClick}
    className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-parchment-panel/90 border border-secondary/40 text-on-surface hover:bg-surface-container-high shadow-xs transition cursor-pointer"
    title="Open pending correspondence"
  >
    <span className="material-symbols-outlined text-[16px] text-secondary">
      markunread_mailbox
    </span>
    <span className="font-body-sm text-[12px] font-medium">
      Dispatch #{dispatchNumber}
    </span>
  </button>
);
