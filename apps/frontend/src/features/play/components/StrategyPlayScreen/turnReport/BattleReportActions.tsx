import React from "react";
import { IconMapPin, IconChevronDown, IconChevronUp } from "@tabler/icons-react";
import type { BattleReportActionsProps } from "./BattleReportActions.types";

export const BattleReportActions: React.FC<BattleReportActionsProps> = ({
  roundsCount,
  isExpanded,
  onFocusMap,
  onToggleRounds,
}) => (
  <div className="flex items-center justify-between pt-1">
    {onFocusMap ? (
      <button
        type="button"
        onClick={onFocusMap}
        className="flex items-center gap-1 text-xs text-[#46606E] hover:text-[#304B59] font-medium cursor-pointer"
        aria-label="Show on map"
      >
        <IconMapPin size={13} />
        <span>Show on map</span>
      </button>
    ) : (
      <div />
    )}

    {roundsCount > 0 ? (
      <button
        type="button"
        onClick={onToggleRounds}
        className="flex items-center gap-1 text-xs text-[#46606E] hover:text-[#304B59] font-medium cursor-pointer"
        aria-expanded={isExpanded}
      >
        <span>Skirmish Phases ({roundsCount})</span>
        {isExpanded ? <IconChevronUp size={13} /> : <IconChevronDown size={13} />}
      </button>
    ) : null}
  </div>
);
