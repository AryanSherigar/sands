import React, { useId } from "react";
import { FilterFieldset } from "./FilterFieldset";
import type { SegmentedControlProps } from "./SegmentedControl.types";

const ANY_LABEL = "Any";

export function SegmentedControl<T extends string>({
  legend,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>): React.ReactElement {
  const groupName = useId();
  const choices: { value: T | null; label: string }[] = [
    { value: null, label: ANY_LABEL },
    ...options,
  ];

  return (
    <FilterFieldset legend={legend}>
      <div className="grid grid-cols-3 rounded-lg border border-border-subtle bg-surface-sunken p-1 text-center text-xs font-medium">
        {choices.map((choice) => (
          <label key={choice.label} className="cursor-pointer">
            <input
              type="radio"
              name={groupName}
              checked={value === choice.value}
              onChange={() => onChange(choice.value)}
              className="peer sr-only"
            />
            <span className="block rounded border border-transparent py-1 text-content-muted transition-colors hover:text-content peer-checked:border-border-subtle peer-checked:bg-surface-raised peer-checked:font-semibold peer-checked:text-content peer-checked:shadow-xs peer-focus-visible:ring-2 peer-focus-visible:ring-accent">
              {choice.label}
            </span>
          </label>
        ))}
      </div>
    </FilterFieldset>
  );
}
