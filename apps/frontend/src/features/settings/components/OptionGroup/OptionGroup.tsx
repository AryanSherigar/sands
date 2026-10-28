import React from "react";
import type { OptionGroupProps } from "./OptionGroup.types";

export const OptionGroup: React.FC<OptionGroupProps> = ({
  label,
  options,
  value,
  onChange,
}) => (
  <div className="space-y-2">
    <span className="block font-sans text-xs font-medium text-content-muted">
      {label}
    </span>
    <div
      role="radiogroup"
      aria-label={label}
      className="flex rounded-md border border-border-strong bg-surface-inset p-0.5"
    >
      {options.map((option) => {
        const isSelected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onChange(option.value)}
            className={`min-h-11 flex-1 rounded px-2 text-center font-sans text-xs transition-colors duration-100 sm:min-h-8 ${
              isSelected
                ? "bg-surface-overlay font-semibold text-content"
                : "text-content-muted hover:text-content"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  </div>
);
