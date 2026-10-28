import React from "react";
import { IconX } from "@tabler/icons-react";
import type { ActiveFilterChipsProps } from "./ActiveFilterChips.types";

const CLOSE_ICON_SIZE = 14;

export const ActiveFilterChips: React.FC<ActiveFilterChipsProps> = ({
  chips,
  onRemove,
  onClearAll,
}) => {
  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border-subtle/60 pt-3">
      <span className="mr-1 text-xs text-content-faint">Filters:</span>
      <ul className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <li key={chip.id}>
            <button
              type="button"
              aria-label={`Remove filter: ${chip.label}`}
              onClick={() => onRemove(chip.id)}
              className="inline-flex h-7 items-center gap-1.5 rounded-full border border-border-subtle bg-surface-raised pl-2.5 pr-1.5 text-xs text-content hover:border-border-strong focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            >
              {chip.label}
              <IconX
                size={CLOSE_ICON_SIZE}
                aria-hidden="true"
                className="text-content-muted"
              />
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={onClearAll}
        className="ml-2 text-xs text-content-faint underline decoration-border-strong underline-offset-4 transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        Clear all
      </button>
    </div>
  );
};
