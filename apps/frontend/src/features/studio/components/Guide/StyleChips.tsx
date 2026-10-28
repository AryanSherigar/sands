import React from "react";
import { STYLE_CHIPS } from "../../constants/styleChips";
import { isStyleChipOn, toggleStyleChip } from "../../lib/styleChips";
import { GuideChip } from "./GuideChip";
import type { StyleChipsProps } from "./Guide.types";

export const StyleChips: React.FC<StyleChipsProps> = ({ document, onChange }) => (
  <div role="group" aria-label="Storytelling styles" className="flex flex-wrap gap-2">
    {STYLE_CHIPS.map((chip) => (
      <GuideChip
        key={chip.id}
        label={chip.label}
        isSelected={isStyleChipOn(document, chip)}
        onClick={() => onChange(toggleStyleChip(document, chip))}
      />
    ))}
  </div>
);
