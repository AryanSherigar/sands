import React from "react";
import { IconDice } from "@tabler/icons-react";
import type { SurpriseMeButtonProps } from "./SurpriseMeButton.types";

const ICON_SIZE = 18;

export const SurpriseMeButton: React.FC<SurpriseMeButtonProps> = ({
  isDisabled,
  onClick,
}) => (
  <button
    type="button"
    disabled={isDisabled}
    onClick={onClick}
    className="group flex h-10 w-full items-center justify-center gap-2 rounded-full border border-border-subtle bg-surface-raised px-4 text-sm font-medium text-content shadow-xs transition-all duration-200 hover:border-border-strong hover:bg-surface-overlay focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
  >
    <IconDice
      size={ICON_SIZE}
      aria-hidden="true"
      className="text-content-muted transition-transform group-hover:rotate-12"
    />
    Surprise me
  </button>
);
