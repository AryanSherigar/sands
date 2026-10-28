import React from "react";
import { Select } from "@/shared/components/ui/Select";
import type { TrackedValueFieldsProps } from "./Advanced.types";

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

export const YesNoField: React.FC<TrackedValueFieldsProps> = ({ field, onChange }) => (
  <label className="block max-w-48 space-y-1 text-meta text-content-muted">
    Starts as
    <Select
      value={field.initial === true ? "yes" : "no"}
      options={YES_NO_OPTIONS}
      onChange={(event) => onChange({ ...field, initial: event.target.value === "yes" })}
    />
  </label>
);
