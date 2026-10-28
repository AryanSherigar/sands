import React from "react";
import { IconBookmark, IconBookmarkFilled } from "@tabler/icons-react";
import type { SaveIconButtonProps } from "./SaveIconButton.types";

const ICON_SIZE = 18;

export const SaveIconButton: React.FC<SaveIconButtonProps> = ({
  scenario,
  onToggleSave,
}) => {
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>): void => {
    event.stopPropagation();
    onToggleSave(scenario);
  };

  return (
    <button
      type="button"
      aria-pressed={scenario.is_bookmarked}
      aria-label={`${scenario.is_bookmarked ? "Saved" : "Save"}: ${scenario.title}`}
      title="Save scenario"
      onClick={handleClick}
      className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg border border-border-subtle bg-surface-sunken text-content-muted transition-colors hover:bg-surface-raised hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      {scenario.is_bookmarked ? (
        <IconBookmarkFilled size={ICON_SIZE} aria-hidden="true" />
      ) : (
        <IconBookmark size={ICON_SIZE} aria-hidden="true" />
      )}
    </button>
  );
};
