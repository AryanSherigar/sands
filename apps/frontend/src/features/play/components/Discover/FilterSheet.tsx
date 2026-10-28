import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { useFilterResultCount } from "../../hooks/useFilterResultCount";
import { buildActiveFilterChips, clearAllFilters } from "../../utils/discoverFilters";
import { FilterPanel } from "./FilterPanel";
import type { FilterSheetProps } from "./FilterSheet.types";

const ESCAPE_KEY = "Escape";

export const FilterSheet: React.FC<FilterSheetProps> = ({
  isOpen,
  appliedFilters,
  isAuthenticated,
  onApply,
  onClose,
  onSignIn,
}) => {
  const [draft, setDraft] = useState(appliedFilters);
  const dialogRef = useRef<HTMLDivElement>(null);
  const resultCount = useFilterResultCount(draft, isOpen);
  useFocusTrap(dialogRef, isOpen);

  useEffect(() => {
    if (isOpen) setDraft(appliedFilters);
  }, [isOpen, appliedFilters]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === ESCAPE_KEY) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleShowResults = (): void => {
    onApply(draft);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex lg:hidden">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Filters"
        tabIndex={-1}
        className="flex h-full w-80 max-w-full flex-col bg-surface-raised shadow-xl"
      >
        <div className="custom-scrollbar flex-1 overflow-y-auto p-4">
          <FilterPanel
            filters={draft}
            hasActiveFilters={buildActiveFilterChips(draft).length > 0}
            isAuthenticated={isAuthenticated}
            onChange={setDraft}
            onClearAll={() => setDraft(clearAllFilters(draft))}
            onSignIn={onSignIn}
          />
        </div>
        <div className="border-t border-border-subtle p-4">
          <Button className="w-full" onClick={handleShowResults}>
            {resultCount === null ? "Show results" : `Show ${resultCount} results`}
          </Button>
        </div>
      </div>
      <button
        type="button"
        aria-label="Close filters"
        onClick={onClose}
        className="flex-1 bg-black/60"
      />
    </div>
  );
};
