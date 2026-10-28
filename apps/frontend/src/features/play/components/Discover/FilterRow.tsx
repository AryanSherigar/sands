import React from "react";
import { ROW_BASE_CLASSES } from "./filterRow.styles";
import type { FilterRowProps } from "./FilterRow.types";

const CHECKED_CLASSES =
  "peer-checked:border-border-subtle peer-checked:bg-surface-raised peer-checked:font-medium peer-checked:text-content";

export const FilterRow: React.FC<FilterRowProps> = ({
  label,
  inputType,
  name,
  isChecked,
  leading,
  onChange,
}) => (
  <label className="block cursor-pointer">
    <input
      type={inputType}
      name={name}
      checked={isChecked}
      onChange={onChange}
      className="peer sr-only"
    />
    <span
      className={`${ROW_BASE_CLASSES} ${CHECKED_CLASSES} peer-focus-visible:ring-2 peer-focus-visible:ring-accent`}
    >
      {leading}
      {label}
    </span>
  </label>
);
