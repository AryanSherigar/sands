import React from "react";
import {
  IconBookmark,
  IconBookmarkFilled,
  IconPencil,
  IconShare2,
} from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { PlayAction } from "./PlayAction";
import type { HeroActionsProps } from "./HeroActions.types";

export const HeroActions: React.FC<HeroActionsProps> = ({
  scenarioId,
  isOwner,
  isDraft,
  isBookmarked,
  isTogglingBookmark,
  isStartingPlaytest,
  onToggleBookmark,
  onShare,
  onPlaytest,
}) => {
  const isAlphaMode = useIsAlphaMode();

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <PlayAction
        scenarioId={scenarioId}
        isDraft={isDraft}
        isStartingPlaytest={isStartingPlaytest}
        onPlaytest={onPlaytest}
      />
      <div className="flex gap-2 sm:contents">
        <Button
          type="button"
          variant="secondary"
          size="lg"
          onClick={onToggleBookmark}
          disabled={isTogglingBookmark}
          aria-pressed={isBookmarked}
          className="flex-1 sm:flex-none"
        >
          {isBookmarked ? (
            <IconBookmarkFilled
              size={18}
              stroke={1.5}
              className="text-accent"
              aria-hidden="true"
            />
          ) : (
            <IconBookmark size={18} stroke={1.5} aria-hidden="true" />
          )}
          <span>{isBookmarked ? "Saved" : "Save"}</span>
        </Button>
        {!isAlphaMode && (
          <Button
            type="button"
            variant="ghost"
            size="lg"
            onClick={onShare}
            className="flex-1 sm:flex-none"
          >
            <IconShare2 size={18} stroke={1.5} aria-hidden="true" />
            <span>Share</span>
          </Button>
        )}
        {isOwner && !isAlphaMode && (
          <ButtonLink
            to={`/studio/${scenarioId}`}
            variant="ghost"
            size="lg"
            className="flex-1 sm:flex-none"
          >
            <IconPencil size={18} stroke={1.5} aria-hidden="true" />
            <span>Edit in Studio</span>
          </ButtonLink>
        )}
      </div>
    </div>
  );
};
