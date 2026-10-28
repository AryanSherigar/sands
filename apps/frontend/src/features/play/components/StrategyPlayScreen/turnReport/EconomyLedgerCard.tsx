import React from "react";
import { IconCoin } from "@tabler/icons-react";
import type { EconomyLedgerCardProps } from "./EconomyLedgerCard.types";
import type { EconomyLedgerLine } from "../../../types/turnReport.types";

const formatGold = (amount: number): string =>
  amount > 0 ? `+${amount}g` : `${amount}g`;

const getGoldColorClass = (amount: number): string => {
  if (amount > 0) return "text-[#5E8A5A]";
  if (amount < 0) return "text-[#A8483E]";
  return "text-[#3A3128]";
};

const renderLine = (line: EconomyLedgerLine, index: number): React.ReactNode => (
  <div
    key={`${line.label}-${index}`}
    className="flex justify-between items-center text-xs py-1 border-b border-[#3A3128]/5 last:border-none"
  >
    <span className="text-[#55493E]">{line.label}</span>
    <span className={`font-mono font-medium ${getGoldColorClass(line.amount)}`}>
      {formatGold(line.amount)}
    </span>
  </div>
);

export const EconomyLedgerCard: React.FC<EconomyLedgerCardProps> = ({
  lines,
  netGold,
}) => (
  <article className="p-3 bg-[#F3EAD3]/70 rounded-lg border border-[#3A3128]/20 space-y-2.5">
    <div className="flex items-center gap-1.5 text-xs text-[#7A6F62]">
      <IconCoin size={14} className="text-[#D2A94A]" />
      <h4 className="font-serif font-semibold text-sm text-[#3A3128]">
        Seasonal Ledger
      </h4>
    </div>

    <div className="space-y-0.5">{lines.map(renderLine)}</div>

    <div className="flex justify-between items-center pt-2 border-t border-[#3A3128]/15 text-xs font-semibold">
      <span className="text-[#3A3128]">Net Balance</span>
      <span className={`font-mono ${getGoldColorClass(netGold)}`}>
        {formatGold(netGold)}
      </span>
    </div>
  </article>
);
