import React from "react";
import type { SortableHeaderProps } from "./SortableHeader.types";

export const SortableHeader: React.FC<SortableHeaderProps> = ({
  column,
  isActive,
  direction,
  onSort,
}) => (
  <th
    scope="col"
    aria-sort={isActive ? direction : "none"}
    className="border-b border-border-subtle px-3 py-2 text-left"
  >
    <button
      type="button"
      onClick={onSort}
      className="font-sans text-sm font-medium text-content-muted hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      {column.label}
    </button>
  </th>
);
