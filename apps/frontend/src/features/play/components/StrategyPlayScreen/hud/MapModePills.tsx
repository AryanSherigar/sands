import type { FC } from "react";
import type { StrategyMapMode } from "../../../stores/strategyPlay.types";
import type { MapModePillsProps } from "./MapModePills.types";

const MAP_MODES: readonly StrategyMapMode[] = [
  "political",
  "terrain",
  "diplomacy",
  "fog",
];

export const MapModePills: FC<MapModePillsProps> = ({
  activeMode = "political",
  onSelectMode,
}) => (
  <nav
    aria-label="Map modes"
    className="flex items-center gap-1 p-1 rounded-full bg-[#F7F0DC]/95 backdrop-blur-xl border border-[#3A3128]/20 shadow-md text-xs"
  >
    {MAP_MODES.map((mode) => (
      <button
        key={mode}
        type="button"
        onClick={() => onSelectMode?.(mode)}
        className={`px-2 py-0.5 rounded-full capitalize font-semibold transition-colors ${
          activeMode === mode
            ? "bg-[#46606E] text-white"
            : "text-[#42474B] hover:text-[#221A12]"
        }`}
      >
        {mode}
      </button>
    ))}
  </nav>
);
