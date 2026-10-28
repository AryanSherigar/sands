import React from "react";
import type { SettingsSwitchProps } from "./SettingsSwitch.types";

export const SettingsSwitch: React.FC<SettingsSwitchProps> = ({
  id,
  label,
  description,
  isChecked,
  isDisabled = false,
  onChange,
}) => (
  <div className="flex items-start justify-between gap-4">
    <div className="space-y-0.5">
      <label htmlFor={id} className="font-sans text-sm font-medium text-content">
        {label}
      </label>
      {description && (
        <p className="font-sans text-xs text-content-faint">{description}</p>
      )}
    </div>
    <input
      id={id}
      type="checkbox"
      role="switch"
      checked={isChecked}
      disabled={isDisabled}
      onChange={(event) => onChange(event.target.checked)}
      className="peer sr-only"
    />
    <label
      htmlFor={id}
      aria-hidden="true"
      className="relative mt-0.5 h-5 w-9 shrink-0 cursor-pointer rounded-full border border-border-strong bg-surface-inset transition-colors duration-100 after:absolute after:left-0.5 after:top-0.5 after:h-3.5 after:w-3.5 after:rounded-full after:bg-content-faint after:transition-transform after:duration-100 peer-checked:bg-primary peer-checked:after:translate-x-4 peer-checked:after:bg-primary-contrast peer-focus-visible:ring-2 peer-focus-visible:ring-primary"
    />
  </div>
);
