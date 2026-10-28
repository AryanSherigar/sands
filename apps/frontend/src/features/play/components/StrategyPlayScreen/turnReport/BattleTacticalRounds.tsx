import React from "react";
import type { BattleTacticalRoundsProps } from "./BattleTacticalRounds.types";
import type { TacticalRound } from "../../../types/turnReport.types";

const renderRound = (round: TacticalRound): React.ReactNode => (
  <div
    key={round.round}
    className="text-xs bg-[#FAF5E8] p-2 rounded border border-[#3A3128]/10 space-y-1"
  >
    <div className="flex justify-between items-center text-[#7A6F62]">
      <span className="font-semibold">Phase {round.round}</span>
      {round.outcomeNote ? (
        <span className="text-[#3A3128] font-medium">{round.outcomeNote}</span>
      ) : null}
    </div>
    <p className="text-[#3A3128]">{round.description}</p>
    <div className="text-[11px] text-[#7A6F62] flex gap-3">
      {round.varnCasualties !== undefined ? (
        <span>Varn: -{round.varnCasualties}</span>
      ) : null}
      {round.rivalCasualties !== undefined ? (
        <span>Enemy: -{round.rivalCasualties}</span>
      ) : null}
    </div>
  </div>
);

export const BattleTacticalRounds: React.FC<BattleTacticalRoundsProps> = ({
  rounds,
}) => {
  if (!rounds || rounds.length === 0) return null;

  return (
    <div className="space-y-1.5 pt-1.5 border-t border-[#3A3128]/10">
      {rounds.map(renderRound)}
    </div>
  );
};
