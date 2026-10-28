import React from "react";
import type { QuickStatsTickerProps } from "./QuickStatsTicker.types";

const formatGold = (amount: number): string =>
  amount > 0 ? `+${amount}g` : `${amount}g`;

const formatStabilityDelta = (delta: number): string =>
  `(${delta > 0 ? `+${delta}` : delta}%)`;

const getGoldColorClass = (amount: number): string => {
  if (amount > 0) return "text-[#5E8A5A]";
  if (amount < 0) return "text-[#A8483E]";
  return "text-[#3A3128]";
};

const getStabilityColorClass = (delta: number): string => {
  if (delta > 0) return "text-[#5E8A5A]";
  if (delta < 0) return "text-[#A8483E]";
  return "text-[#7A6F62]";
};

export const QuickStatsTicker: React.FC<QuickStatsTickerProps> = ({ stats }) => {
  const goldClass = getGoldColorClass(stats.netGold);
  const stabClass = getStabilityColorClass(stats.stabilityDelta);

  return (
    <div className="grid grid-cols-4 gap-2 p-2 bg-[#F3EAD3]/60 rounded-lg border border-[#3A3128]/15">
      <div className="flex flex-col">
        <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
          Net Gold
        </span>
        <span className={`text-sm font-semibold font-mono ${goldClass}`}>
          {formatGold(stats.netGold)}
        </span>
      </div>

      <div className="flex flex-col">
        <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
          Casualties
        </span>
        <span className="text-sm font-semibold font-mono text-[#A8483E]">
          {stats.totalCasualties.toLocaleString()}
        </span>
      </div>

      <div className="flex flex-col">
        <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
          Stability
        </span>
        <div className="flex items-baseline gap-1">
          <span className="text-sm font-semibold font-mono text-[#3A3128]">
            {stats.stability}%
          </span>
          <span className={`text-xs font-mono font-medium ${stabClass}`}>
            {formatStabilityDelta(stats.stabilityDelta)}
          </span>
        </div>
      </div>

      <div className="flex flex-col">
        <span className="text-[11px] font-serif uppercase tracking-wider text-[#7A6F62]">
          Manpower
        </span>
        <span className="text-sm font-semibold font-mono text-[#3A3128]">
          {stats.manpower.toLocaleString()}
        </span>
      </div>
    </div>
  );
};
