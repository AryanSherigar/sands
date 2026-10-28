import React from "react";
import { setBound } from "../../../lib/trackedValueEditing";
import type { TrackedValueFieldsProps } from "./Advanced.types";
import { NumberField } from "./NumberField";

export const NumberValueFields: React.FC<TrackedValueFieldsProps> = ({ field, onChange }) => (
  <div className="grid grid-cols-3 gap-3">
    <NumberField
      label="Starts at"
      value={typeof field.initial === "number" ? field.initial : undefined}
      onChange={(value) => onChange({ ...field, initial: value ?? 0 })}
    />
    <NumberField label="Lowest" value={field.min} onChange={(value) => onChange(setBound(field, "min", value))} />
    <NumberField label="Highest" value={field.max} onChange={(value) => onChange(setBound(field, "max", value))} />
  </div>
);
