import React from "react";
import { IconCheck } from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import type { GuideChipProps } from "./Guide.types";

export const GuideChip: React.FC<GuideChipProps> = ({
  label,
  isSelected = false,
  badge,
  onClick,
}) => (
  <button
    type="button"
    aria-pressed={isSelected}
    onClick={onClick}
    className={cn(
      "inline-flex items-center gap-1.5 rounded-sm border px-3 py-1.5 text-meta transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary",
      isSelected
        ? "border-primary bg-primary text-primary-contrast"
        : "border-border-strong bg-surface-inset text-content-muted hover:text-content",
    )}
  >
    {isSelected && <IconCheck size={14} aria-hidden="true" />}
    {label}
    {badge && <span className="text-micro font-semibold uppercase">{badge}</span>}
  </button>
);
