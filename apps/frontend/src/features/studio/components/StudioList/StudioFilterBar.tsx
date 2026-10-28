import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { cn } from "@/shared/lib/cn";
import { STUDIO_TABS } from "../../constants/studio-list";
import type { StudioFilterBarProps } from "./StudioList.types";

export const StudioFilterBar: React.FC<StudioFilterBarProps> = ({
  tab,
  onTabChange,
  query,
  onQueryChange,
  counts,
}) => (
  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div
      role="group"
      aria-label="Filter by status"
      className="flex gap-1 overflow-x-auto rounded-md bg-surface-sunken p-1"
    >
      {STUDIO_TABS.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          aria-pressed={tab === value}
          onClick={() => onTabChange(value)}
          className={cn(
            "shrink-0 rounded-sm px-4 py-1.5 font-sans text-sm font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary",
            tab === value
              ? "bg-surface-raised text-content"
              : "text-content-muted hover:text-content",
          )}
        >
          {label}
          {counts && (
            <span className="ml-1.5 font-mono text-xs text-content-faint">
              {counts[value]}
            </span>
          )}
        </button>
      ))}
    </div>
    <div className="w-full sm:w-64">
      <Input
        type="search"
        aria-label="Filter worlds"
        placeholder="Filter worlds…"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
    </div>
  </div>
);
