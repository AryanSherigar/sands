import React from "react";
import { IconBuildingCastle } from "@tabler/icons-react";
import type { SettlementPinProps } from "../StrategyMap.types";

function renderBadge(isSelected: boolean): React.ReactElement {
  const selectedClass = isSelected ? "ring-2 ring-[#46606E]" : "";
  return (
    <div
      className={`w-9 h-9 rounded-full bg-[#F7F0DC]/95 border border-[#3A3128]/25 shadow-md flex items-center justify-center text-[#46606E] transition-transform group-hover:scale-110 ${selectedClass}`}
    >
      <IconBuildingCastle size={18} stroke={1.75} />
    </div>
  );
}

export const SettlementPin: React.FC<SettlementPinProps> = ({
  name,
  regionId,
  coords,
  isSelected = false,
  onClick,
}) => {
  const handleClick = (event: React.MouseEvent) => {
    event.stopPropagation();
    onClick(regionId);
  };

  return (
    <div
      style={{ left: `${coords.x}px`, top: `${coords.y}px` }}
      className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group z-20 flex flex-col items-center"
      onClick={handleClick}
    >
      {renderBadge(isSelected)}
      <div className="mt-1 px-2 py-0.5 rounded-full bg-[#F7F0DC]/90 border border-[#3A3128]/15 shadow-sm text-[11px] font-bold text-[#221A12] whitespace-nowrap">
        {name}
      </div>
    </div>
  );
};
