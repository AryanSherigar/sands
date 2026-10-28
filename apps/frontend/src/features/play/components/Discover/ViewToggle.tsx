import React from "react";
import { IconLayoutGrid, IconList } from "@tabler/icons-react";
import { VIEW_OPTIONS } from "../../constants/discover.constants";
import type { DiscoverView } from "../../types/discover.types";
import type { ViewToggleProps } from "./ViewToggle.types";

const ICON_SIZE = 18;

const VIEW_ICONS: Record<DiscoverView, React.ReactNode> = {
  list: <IconList size={ICON_SIZE} aria-hidden="true" />,
  grid: <IconLayoutGrid size={ICON_SIZE} aria-hidden="true" />,
};

export const ViewToggle: React.FC<ViewToggleProps> = ({ value, onChange }) => (
  <div
    role="radiogroup"
    aria-label="View"
    className="flex items-center rounded-lg border border-border-subtle bg-surface-sunken p-0.5"
  >
    {VIEW_OPTIONS.map((option) => (
      <button
        key={option.value}
        type="button"
        role="radio"
        aria-checked={value === option.value}
        aria-label={option.label}
        title={`${option.label} view`}
        onClick={() => onChange(option.value)}
        className={`flex h-8 w-8 items-center justify-center rounded transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent ${
          value === option.value
            ? "bg-surface-raised text-content shadow-xs"
            : "text-content-muted hover:bg-surface-raised/50 hover:text-content"
        }`}
      >
        {VIEW_ICONS[option.value]}
      </button>
    ))}
  </div>
);
