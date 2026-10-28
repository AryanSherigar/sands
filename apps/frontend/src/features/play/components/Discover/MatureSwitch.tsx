import React from "react";
import type { MatureSwitchProps } from "./MatureSwitch.types";

export const MatureSwitch: React.FC<MatureSwitchProps> = ({
  isChecked,
  onChange,
}) => (
  <label className="flex cursor-pointer items-center justify-between gap-3 px-3 text-sm text-content-muted">
    Show mature stories
    <input
      type="checkbox"
      role="switch"
      checked={isChecked}
      onChange={onChange}
      className="peer sr-only"
    />
    <span
      aria-hidden="true"
      className="relative h-5 w-9 shrink-0 rounded-full border border-border-subtle bg-surface-sunken transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-3.5 after:w-3.5 after:rounded-full after:bg-content-faint after:transition-transform peer-checked:bg-surface-raised peer-checked:after:translate-x-4 peer-checked:after:bg-content peer-focus-visible:ring-2 peer-focus-visible:ring-accent"
    />
  </label>
);
