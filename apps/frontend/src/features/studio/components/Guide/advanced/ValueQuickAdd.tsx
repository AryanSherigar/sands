import React from "react";
import { QUICK_ADD_VALUES, OWN_VALUE_INPUT } from "../../../constants/valueQuickAdd";
import { GuideChip } from "../GuideChip";
import type { ValueQuickAddProps } from "./Advanced.types";

export const ValueQuickAdd: React.FC<ValueQuickAddProps> = ({ existingLabels, onAdd }) => (
  <section aria-label="Quick add" className="space-y-2">
    <p className="text-meta font-medium text-content-muted">Quick add</p>
    <div className="flex flex-wrap gap-2">
      {QUICK_ADD_VALUES.map((quick) => (
        <GuideChip
          key={quick.id}
          label={quick.label}
          isSelected={existingLabels.has(quick.label.toLowerCase())}
          onClick={() => {
            if (!existingLabels.has(quick.label.toLowerCase())) onAdd(quick.input);
          }}
        />
      ))}
      <GuideChip label="Your own…" onClick={() => onAdd(OWN_VALUE_INPUT)} />
    </div>
  </section>
);
