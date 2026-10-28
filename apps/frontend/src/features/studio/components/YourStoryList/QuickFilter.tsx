import React from "react";
import { IconSearch } from "@tabler/icons-react";
import type { QuickFilterProps } from "./YourStoryList.types";

export const QuickFilter: React.FC<QuickFilterProps> = ({ value, onChange }) => (
  <label className="relative block">
    <span className="sr-only">Filter your story by name</span>
    <IconSearch
      size={16}
      aria-hidden="true"
      className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-content-faint"
    />
    <input
      type="search"
      value={value}
      placeholder="Quick filter"
      onChange={(event) => onChange(event.target.value)}
      className="h-9 w-full rounded-md border border-border-subtle bg-surface-inset pl-8 pr-2 text-meta text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
    />
  </label>
);
