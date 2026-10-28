import React from "react";
import { enumOptionValues } from "../../lib/stateSchemaFields";
import { RandomInitialPickerProps } from "./RandomInitialPicker.types";

export const RandomInitialPicker: React.FC<RandomInitialPickerProps> = ({
  options,
  value,
  onChange,
}) => {
  const choices = enumOptionValues(options);
  const selected = value ?? [];
  if (choices.length < 2) return null;

  const handleToggle = (choice: string): void => {
    const next = selected.includes(choice)
      ? selected.filter((item) => item !== choice)
      : choices.filter((item) => item === choice || selected.includes(item));
    onChange(next.length ? next : undefined);
  };

  return (
    <fieldset className="text-xs text-content-muted">
      <legend>Random starting value (each playthrough draws one)</legend>
      <div className="mt-1 flex flex-wrap gap-3">
        {choices.map((choice) => (
          <label key={choice} className="flex items-center gap-1">
            <input
              type="checkbox"
              aria-label={`Random start: ${choice}`}
              checked={selected.includes(choice)}
              onChange={() => handleToggle(choice)}
            />
            {choice || "(empty)"}
          </label>
        ))}
      </div>
    </fieldset>
  );
};
