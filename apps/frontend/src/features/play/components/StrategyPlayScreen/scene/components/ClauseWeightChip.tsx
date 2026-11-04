import React from "react";
import type { ClauseWeightChipProps } from "./ClauseWeightChip.types";

const BAND_COPY = {
  light: { label: "Light weight", chipClass: "bg-meadow-green/20 text-meadow-green" },
  moderate: { label: "Moderate weight", chipClass: "bg-amber-500/20 text-amber-300" },
  heavy: { label: "Heavy weight", chipClass: "bg-[#A8483E]/20 text-rose-300" },
} as const;

export const ClauseWeightChip: React.FC<ClauseWeightChipProps> = ({ band }) => {
  const copy = BAND_COPY[band];
  return (
    <span
      className={`inline-block mt-1 ml-4 font-sans text-[10px] uppercase px-2 py-0.5 font-bold rounded ${copy.chipClass}`}
    >
      {copy.label}
    </span>
  );
};
