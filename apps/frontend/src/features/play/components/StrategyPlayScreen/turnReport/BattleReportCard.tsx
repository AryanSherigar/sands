import React, { useState } from "react";
import type { BattleReportCardProps } from "./BattleReportCard.types";
import { BattleReportHeader } from "./BattleReportHeader";
import { BattleCasualtiesRow } from "./BattleCasualtiesRow";
import { BattleReportActions } from "./BattleReportActions";
import { BattleTacticalRounds } from "./BattleTacticalRounds";

export const BattleReportCard: React.FC<BattleReportCardProps> = ({
  battle,
  onFocusMap,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const handleToggle = () => setIsExpanded((prev) => !prev);
  const handleFocus = () => onFocusMap?.(battle.regionId);

  return (
    <article className="p-3 bg-[#F3EAD3]/70 rounded-lg border border-[#3A3128]/20 space-y-2.5">
      <BattleReportHeader battle={battle} />
      <p className="text-xs text-[#55493E] leading-relaxed">{battle.summary}</p>
      <BattleCasualtiesRow battle={battle} />
      <BattleReportActions
        regionId={battle.regionId}
        roundsCount={battle.rounds?.length ?? 0}
        isExpanded={isExpanded}
        onFocusMap={onFocusMap ? handleFocus : undefined}
        onToggleRounds={handleToggle}
      />
      {isExpanded ? <BattleTacticalRounds rounds={battle.rounds} /> : null}
    </article>
  );
};
