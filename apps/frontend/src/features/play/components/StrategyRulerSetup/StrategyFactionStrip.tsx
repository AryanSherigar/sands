import React from "react";
import type { StrategyFactionStripProps } from "./StrategyRulerSetup.types";

const DEFAULT_ROLE_TAGS = ["Martial", "Diplomacy", "Vanguard", "Merchant"];

function getFactionTagline(faction: StrategyFactionStripProps["factions"][number]): string {
  if (faction.tagline) return faction.tagline;
  if (faction.manpower >= 12000) return "High Manpower";
  if (faction.treasury >= 300) return "Golden Trade Routes";
  if ((faction.provinces_count ?? 1) >= 4) return "Vast Territories";
  return "Timber & Alliances";
}

export const StrategyFactionStrip: React.FC<StrategyFactionStripProps> = ({
  factions,
  activeFactionId,
  onSelectFaction,
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2" id="factionSelector">
      {factions.map((faction, idx) => {
        const isSelected = faction.id === activeFactionId;
        const roleTag =
          faction.role_tag ??
          (isSelected ? "Selected" : DEFAULT_ROLE_TAGS[idx % DEFAULT_ROLE_TAGS.length]);
        const tagline = getFactionTagline(faction);

        return (
          <button
            key={faction.id}
            type="button"
            onClick={() => onSelectFaction(faction.id)}
            className={`flex flex-col text-left p-2.5 rounded-lg transition-all cursor-pointer ${
              isSelected
                ? "bg-[#f5e5d8] shadow-md text-[#2e4856] ring-2 ring-[#2e4856]"
                : "bg-[#F7F0DC]/75 hover:bg-[#F7F0DC] shadow-xs text-[#221a12] border border-[#3A3128]/10"
            }`}
          >
            <div className="flex items-center justify-between w-full mb-1">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: faction.color }}
              />
              <span
                className={`text-[10px] uppercase font-bold tracking-wider font-['Manrope',sans-serif] ${
                  isSelected ? "text-[#2e4856]" : "text-[#72787c]"
                }`}
              >
                {isSelected ? "Selected" : roleTag}
              </span>
            </div>
            <span
              className={`text-[15px] font-semibold truncate leading-tight font-['EB_Garamond',serif] ${
                isSelected ? "text-[#2e4856]" : "text-[#221a12]"
              }`}
            >
              {faction.name}
            </span>
            <span className="text-[11px] text-[#42474b] truncate font-['Manrope',sans-serif] mt-0.5">
              {tagline}
            </span>
          </button>
        );
      })}
    </div>
  );
};
