import React from "react";
import {
  IconBookmark,
  IconHistory,
  IconNotes,
} from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { LIBRARY_OPTIONS } from "../../constants/discover.constants";
import type { DiscoverLibrary } from "../../types/discover.types";
import { FilterFieldset } from "./FilterFieldset";
import { ROW_ACTIVE_CLASSES, ROW_BASE_CLASSES } from "./filterRow.styles";
import type { LibraryFilterProps } from "./LibraryFilter.types";

const ICON_SIZE = 18;

const LIBRARY_ICONS: Record<DiscoverLibrary, React.ReactNode> = {
  played: <IconHistory size={ICON_SIZE} aria-hidden="true" />,
  saved: <IconBookmark size={ICON_SIZE} aria-hidden="true" />,
  created: <IconNotes size={ICON_SIZE} aria-hidden="true" />,
};

export const LibraryFilter: React.FC<LibraryFilterProps> = ({
  value,
  isAuthenticated,
  onChange,
  onSignIn,
}) => {
  if (!isAuthenticated) {
    return (
      <FilterFieldset legend="You">
        <p className="px-3 text-sm text-content-muted">
          Sign in to see stories you&apos;ve played and saved
        </p>
        <div className="px-3">
          <Button variant="secondary" size="sm" onClick={onSignIn}>
            Sign in
          </Button>
        </div>
      </FilterFieldset>
    );
  }

  return (
    <FilterFieldset legend="You">
      {LIBRARY_OPTIONS.map((option) => {
        const isActive = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange(isActive ? null : option.value)}
            className={`${ROW_BASE_CLASSES} w-full text-left focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent ${
              isActive ? ROW_ACTIVE_CLASSES : ""
            }`}
          >
            {LIBRARY_ICONS[option.value]}
            {option.label}
          </button>
        );
      })}
    </FilterFieldset>
  );
};
