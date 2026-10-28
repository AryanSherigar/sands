import type { FC } from "react";
import type { StatChipProps } from "./StatChip.types";

export const StatChip: FC<StatChipProps> = ({
  icon,
  value,
  trend,
  tooltipTitle,
  tooltipDesc,
}) => (
  <div className="group relative flex items-center gap-1.5 px-2 py-0.5 rounded-full hover:bg-[#FBEBDE]/80 cursor-help transition-colors">
    <span className="text-xs flex items-center text-[#46606E]">{icon}</span>
    <span className="text-xs font-bold font-mono text-[#221A12]">{value}</span>
    {trend ? <span className="text-[9px] font-bold text-[#5E8A5A]">{trend}</span> : null}

    <div className="absolute top-full right-0 mt-2 hidden group-hover:flex flex-col p-2.5 bg-[#382F26] text-[#FEEEE0] rounded-lg shadow-xl text-[11px] w-56 z-50 pointer-events-none">
      <span className="font-bold text-[#FED16E] mb-1">{tooltipTitle}</span>
      <span className="leading-snug text-[#FEEEE0]/90">{tooltipDesc}</span>
    </div>
  </div>
);
