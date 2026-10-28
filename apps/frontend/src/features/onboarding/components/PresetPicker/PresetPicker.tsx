import React from "react";
import type { PresetPickerProps } from "./PresetPicker.types";

export const PresetPicker: React.FC<PresetPickerProps> = ({
  label,
  options,
  selectedUrl,
  onSelect,
}) => (
  <fieldset>
    <legend className="mb-1.5 text-xs font-medium uppercase tracking-wider text-content-faint">
      {label} (optional)
    </legend>
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          aria-label={`${label}: ${option.name}`}
          aria-pressed={selectedUrl === option.url}
          onClick={() => onSelect(option.url)}
          className={`h-14 w-14 overflow-hidden rounded-md border transition focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent ${
            selectedUrl === option.url
              ? "border-accent shadow-accent-glow"
              : "border-border-subtle hover:border-border-strong"
          }`}
        >
          <img src={option.url} alt="" className="h-full w-full object-cover" />
        </button>
      ))}
    </div>
  </fieldset>
);
