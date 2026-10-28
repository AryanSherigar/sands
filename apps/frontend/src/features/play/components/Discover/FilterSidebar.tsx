import React from "react";
import { FilterPanel } from "./FilterPanel";
import { SurpriseMeButton } from "./SurpriseMeButton";
import type { FilterSidebarProps } from "./FilterSidebar.types";

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  isSurpriseDisabled,
  onSurprise,
  ...panelProps
}) => (
  <aside
    aria-label="Filters"
    className="custom-scrollbar sticky top-20 hidden max-h-[calc(100vh-6rem)] w-[260px] shrink-0 flex-col gap-6 self-start overflow-y-auto pb-6 lg:flex"
  >
    <SurpriseMeButton isDisabled={isSurpriseDisabled} onClick={onSurprise} />
    <FilterPanel {...panelProps} />
  </aside>
);
