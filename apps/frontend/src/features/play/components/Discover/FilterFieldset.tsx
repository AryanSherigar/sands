import React from "react";
import type { FilterFieldsetProps } from "./FilterFieldset.types";

export const FilterFieldset: React.FC<FilterFieldsetProps> = ({
  legend,
  children,
}) => (
  <fieldset className="flex flex-col gap-1 border-0 p-0">
    <legend className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-content-faint">
      {legend}
    </legend>
    {children}
  </fieldset>
);
