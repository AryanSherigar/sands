import React from "react";
import { Select } from "@/shared/components/ui/Select";
import { ResultSelectProps } from "./ResultSelect.types";

export const ResultSelect: React.FC<ResultSelectProps> = ({
  label,
  value,
  choices,
  isOptional = false,
  helpText,
  onChange,
}) => {
  const placeholder = isOptional ? "No result (no penalty)" : "Choose a result";
  const options = [
    { value: "", label: placeholder },
    ...choices.filter(Boolean).map((choice) => ({ value: choice, label: choice })),
  ];

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    onChange(event.target.value);

  return (
    <div>
      <p className="mb-1 text-sm text-content-muted">{label}</p>
      <Select
        aria-label={label}
        options={options}
        value={value}
        onChange={handleChange}
      />
      {helpText && <p className="mt-1 text-xs text-content-faint">{helpText}</p>}
    </div>
  );
};
