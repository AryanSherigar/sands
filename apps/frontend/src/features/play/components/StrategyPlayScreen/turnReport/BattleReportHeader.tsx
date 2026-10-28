import React from "react";
import { IconSwords } from "@tabler/icons-react";
import type { BattleReportHeaderProps } from "./BattleReportHeader.types";
import type { BattleOutcome } from "../../../types/turnReport.types";

const formatOutcome = (outcome: BattleOutcome): string => {
  switch (outcome) {
    case "decisive_victory":
      return "Decisive Victory";
    case "marginal_victory":
      return "Marginal Victory";
    case "defeat":
      return "Defeat";
    case "stalemate":
      return "Stalemate";
  }
};

const getOutcomeClass = (outcome: BattleOutcome): string => {
  switch (outcome) {
    case "decisive_victory":
      return "bg-[#5E8A5A]/15 text-[#3E653A] border-[#5E8A5A]/30";
    case "marginal_victory":
      return "bg-[#46606E]/15 text-[#304B59] border-[#46606E]/30";
    case "defeat":
      return "bg-[#A8483E]/15 text-[#88362D] border-[#A8483E]/30";
    case "stalemate":
      return "bg-[#3A3128]/10 text-[#55493E] border-[#3A3128]/20";
  }
};

export const BattleReportHeader: React.FC<BattleReportHeaderProps> = ({ battle }) => (
  <div className="flex items-start justify-between gap-2">
    <div className="space-y-0.5">
      <div className="flex items-center gap-1.5 text-xs text-[#7A6F62]">
        <IconSwords size={14} className="text-[#A8483E]" />
        <span>{battle.regionName}</span>
      </div>
      <h4 className="font-serif font-semibold text-sm text-[#3A3128]">
        {battle.name}
      </h4>
    </div>
    <span
      className={`px-2 py-0.5 text-[11px] font-medium rounded border ${getOutcomeClass(battle.outcome)}`}
    >
      {formatOutcome(battle.outcome)}
    </span>
  </div>
);
