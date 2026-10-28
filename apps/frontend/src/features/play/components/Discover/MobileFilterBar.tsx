import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { QuickGenreChips } from "./QuickGenreChips";
import type { MobileFilterBarProps } from "./MobileFilterBar.types";

export const MobileFilterBar: React.FC<MobileFilterBarProps> = ({
  selectedGenres,
  activeFilterCount,
  onToggleGenre,
  onOpenFilters,
}) => (
  <div className="flex flex-col gap-2 pb-3 lg:hidden">
    <Button variant="secondary" size="sm" className="w-fit" onClick={onOpenFilters}>
      Filters
      {activeFilterCount > 0 && (
        <span className="rounded-full bg-accent px-1.5 text-xs text-accent-contrast">
          {activeFilterCount}
        </span>
      )}
    </Button>
    <QuickGenreChips selected={selectedGenres} onToggle={onToggleGenre} />
  </div>
);
