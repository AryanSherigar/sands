import React from "react";
import { IconLock, IconSkull, IconTrophy } from "@tabler/icons-react";
import { OUTCOME_LABELS } from "../../../constants/endings.constants";
import type { EndingSlotItemProps } from "./EndingSlotItem.types";

const SLOT_CLASSES = "flex items-center gap-3 rounded-md border px-3 py-2";

export const EndingSlotItem: React.FC<EndingSlotItemProps> = ({ slot }) => {
  if (!slot.is_found) {
    return (
      <li
        className={`${SLOT_CLASSES} border-dashed border-border-strong text-content-faint`}
      >
        <IconLock size={20} stroke={1.5} aria-hidden="true" />
        <span className="text-sm">Undiscovered</span>
      </li>
    );
  }
  const OutcomeIcon = slot.outcome_tag === "lose" ? IconSkull : IconTrophy;
  return (
    <li
      className={`${SLOT_CLASSES} border-border-subtle bg-surface-inset text-content`}
    >
      <OutcomeIcon size={20} stroke={1.5} aria-hidden="true" />
      <span className="flex flex-col">
        <span className="text-xs text-content-muted">
          {slot.outcome_tag ? OUTCOME_LABELS[slot.outcome_tag] : "Ending"}
        </span>
        <span className="text-sm font-medium">{slot.title}</span>
      </span>
    </li>
  );
};
