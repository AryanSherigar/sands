import React from "react";
import { IconX } from "@tabler/icons-react";
import type { ReportDrawerHeaderProps } from "./ReportDrawerHeader.types";

export const ReportDrawerHeader: React.FC<ReportDrawerHeaderProps> = ({
  turn,
  seasonTitle,
  headline,
  onClose,
}) => (
  <header className="p-4 border-b border-[#3A3128]/15 bg-[#F3EAD3]/40">
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase rounded bg-[#3A3128]/10 text-[#3A3128]">
            Turn {turn}
          </span>
          <span className="text-xs font-serif text-[#7A6F62]">{seasonTitle}</span>
        </div>
        <h2 className="text-lg font-serif font-bold text-[#3A3128] mt-1 leading-snug">
          {headline}
        </h2>
      </div>

      <button
        type="button"
        aria-label="Close report"
        onClick={onClose}
        className="p-1 rounded text-[#7A6F62] hover:text-[#3A3128] hover:bg-[#3A3128]/10 transition-colors flex items-center gap-1 text-xs"
      >
        <IconX size={16} />
        <span className="text-[10px] uppercase font-mono tracking-wider opacity-70">
          Esc
        </span>
      </button>
    </div>
  </header>
);
