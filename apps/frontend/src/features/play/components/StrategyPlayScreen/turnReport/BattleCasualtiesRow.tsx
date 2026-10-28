import React from "react";
import type { BattleCasualtiesRowProps } from "./BattleCasualtiesRow.types";

const formatWarScore = (delta: number): string =>
  delta > 0 ? `+${delta} War Score` : `${delta} War Score`;

export const BattleCasualtiesRow: React.FC<BattleCasualtiesRowProps> = ({
  battle,
}) => (
  <div className="flex items-center justify-between text-xs bg-[#FAF5E8]/80 px-2.5 py-1.5 rounded border border-[#3A3128]/10 font-mono">
    <span className="text-[#3A3128]">
      Losses: <span className="text-[#A8483E]">-{battle.varnLosses}</span> vs{" "}
      <span className="text-[#5E8A5A]">-{battle.rivalLosses}</span>
    </span>
    <span className="text-xs font-serif font-medium text-[#46606E]">
      {formatWarScore(battle.warScoreDelta)}
    </span>
  </div>
);
