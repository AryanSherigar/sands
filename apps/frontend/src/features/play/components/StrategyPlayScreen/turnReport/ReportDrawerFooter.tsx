import React from "react";
import type { ReportDrawerFooterProps } from "./ReportDrawerFooter.types";

export const ReportDrawerFooter: React.FC<ReportDrawerFooterProps> = ({
  autoShowTurnReport,
  onToggleAutoShow,
  onDismiss,
  onContinue,
}) => (
  <footer className="p-3 border-t border-[#3A3128]/15 bg-[#F3EAD3]/60 space-y-2.5">
    <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-[#55493E]">
      <input
        type="checkbox"
        checked={autoShowTurnReport}
        onChange={(event) => onToggleAutoShow(event.target.checked)}
        className="rounded border-[#3A3128]/30 text-[#46606E] focus:ring-0 cursor-pointer"
      />
      <span>Show report after each turn</span>
    </label>

    <div className="flex items-center justify-end gap-2">
      <button
        type="button"
        onClick={onDismiss}
        className="px-3 py-1.5 text-xs font-serif text-[#55493E] hover:text-[#3A3128] hover:bg-[#3A3128]/10 rounded border border-[#3A3128]/20 transition-colors"
      >
        Dismiss Ledger
      </button>

      <button
        type="button"
        onClick={onContinue}
        className="px-3.5 py-1.5 text-xs font-serif font-semibold text-white bg-[#46606E] hover:bg-[#39505C] rounded shadow-sm transition-colors"
      >
        Continue to next turn
      </button>
    </div>
  </footer>
);
