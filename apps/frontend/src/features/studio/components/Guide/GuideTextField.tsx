import React, { useId } from "react";
import { cn } from "@/shared/lib/cn";
import type { GuideTextFieldProps } from "./Guide.types";

export const GuideTextField: React.FC<GuideTextFieldProps> = ({
  label,
  helper,
  value,
  maxLength,
  placeholder,
  isLarge = false,
  onChange,
}) => {
  const fieldId = useId();
  const helperId = `${fieldId}-helper`;

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    onChange(event.target.value.slice(0, maxLength));

  return (
    <div className="space-y-2">
      <label htmlFor={fieldId} className="block text-meta font-medium text-content-muted">
        {label}
      </label>
      <input
        id={fieldId}
        type="text"
        value={value}
        maxLength={maxLength}
        placeholder={placeholder}
        aria-describedby={helperId}
        onChange={handleChange}
        className={cn(
          "w-full rounded-lg border border-border-strong bg-surface-inset px-4 text-content placeholder:text-content-faint transition-colors focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20",
          isLarge ? "h-14 text-body-lg" : "h-11 text-body",
        )}
      />
      <p id={helperId} className="flex justify-between gap-4 text-micro text-content-faint">
        <span>{helper}</span>
        <span aria-label={`${value.length} of ${maxLength} characters`}>
          {value.length} / {maxLength}
        </span>
      </p>
    </div>
  );
};
