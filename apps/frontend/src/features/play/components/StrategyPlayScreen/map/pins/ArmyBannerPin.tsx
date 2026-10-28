import React from "react";
import { IconSwords } from "@tabler/icons-react";
import type { ArmyBannerPinProps } from "../StrategyMap.types";

function getHostileClass(isHostile: boolean): string {
  if (isHostile) {
    return "bg-[#A8483E] text-white border-[#A8483E]";
  }
  return "bg-[#46606E] text-white border-[#46606E]";
}

function renderBannerContent(
  displayName: string,
  troopCount: number,
): React.ReactElement {
  return (
    <>
      <IconSwords size={12} stroke={2} className="shrink-0" />
      <div className="flex flex-col leading-tight">
        <span className="text-[9px] font-bold uppercase tracking-wider">
          {displayName}
        </span>
        <span className="text-[11px] font-bold">
          {troopCount.toLocaleString()}
        </span>
      </div>
    </>
  );
}

export const ArmyBannerPin: React.FC<ArmyBannerPinProps> = ({
  armyId,
  commanderName,
  troopCount,
  coords,
  isHostile = false,
  isSelected = false,
  onClick,
}) => {
  const handleClick = (event: React.MouseEvent) => {
    event.stopPropagation();
    onClick(armyId);
  };

  const badgeClass = `${getHostileClass(isHostile)} ${isSelected ? "ring-2 ring-[#D2A94A]" : ""}`;
  const displayName = commanderName ?? (isHostile ? "Hostile Host" : "Royal Host");

  return (
    <div
      style={{ left: `${coords.x}px`, top: `${coords.y}px` }}
      className="absolute -translate-x-1/2 -translate-y-1/2 -mt-12 cursor-pointer z-30 group"
      onClick={handleClick}
    >
      <div
        className={`px-2 py-1 rounded-md shadow-lg border flex items-center gap-1.5 transition-transform group-hover:scale-105 ${badgeClass}`}
      >
        {renderBannerContent(displayName, troopCount)}
      </div>
    </div>
  );
};
