import type { TacticalOddsEstimate } from "../StrategyWarCouncil.types";
import { FactorItemPopover } from "./FactorItemPopover";

export interface OddsLedgerProps {
  odds: TacticalOddsEstimate;
  playerFactionName: string;
  enemyFactionName: string;
}

export function OddsLedger({ odds, playerFactionName, enemyFactionName }: OddsLedgerProps) {
  const isPositive = odds.balancePercent >= 50;
  const scoreText = odds.isRange
    ? `${odds.minPercent}%–${odds.maxPercent}% ${odds.tierText}`
    : `+${odds.balancePercent}% ${odds.tierText}`;

  return (
    <div className="p-3 rounded-xl bg-[#fff8f4]/90 shadow-sm border border-[#3A3128]/10 flex flex-col gap-2">
      <div className="flex items-center justify-between border-b pb-1.5 border-[#3A3128]/10">
        <div>
          <p className="text-[10px] tracking-wider uppercase text-[#42474b]">Odds Ledger</p>
          <h2 className="font-serif text-[17px] text-[#2e4856] leading-tight">Tactical Balance</h2>
          <p className="text-[10px] text-[#72787c] italic">Rough estimate, not the battle engine's calculation</p>
        </div>
        <span className={`text-[15px] font-bold ${isPositive ? "text-[#5E8A5A]" : "text-[#7c2820]"}`}>
          {scoreText}
        </span>
      </div>

      {/* Meter Bar */}
      <div
        role="meter"
        aria-label="Estimated balance of forces"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={odds.balancePercent}
        className="relative h-2 w-full overflow-hidden rounded-full bg-[#7c2820] shadow-inner"
      >
        <div
          className="absolute inset-0 origin-left bg-[#5E8A5A] transition-transform duration-500 ease-out"
          style={{ transform: `scaleX(${odds.balancePercent / 100})` }}
        />
      </div>
      <div className="flex justify-between text-[11px] text-[#42474b] font-medium">
        <span>{playerFactionName} ({odds.balancePercent}%)</span>
        <span>{enemyFactionName} ({100 - odds.balancePercent}%)</span>
      </div>

      {/* Factors List */}
      <div className="flex flex-col gap-1.5 mt-0.5">
        {odds.factors.map((factor) => (
          <FactorItemPopover key={factor.id} factor={factor} />
        ))}
      </div>
      <p className="text-[10px] text-[#42474b] italic text-center">Hover factor to inspect tactical provenance</p>
    </div>
  );
}
