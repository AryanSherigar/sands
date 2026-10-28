import React from "react";
import {
  IconBookmark,
  IconBookmarkFilled,
  IconPlayerPlayFilled,
} from "@tabler/icons-react";
import { usePlayScenario } from "../hooks/usePlayScenario";
import { useSaveScenario } from "../hooks/useSaveScenario";
import type { PosterCardActionsProps } from "./PosterCardActions.types";

const ACTION_BUTTON_CLASSES =
  "pointer-events-auto inline-flex h-8 items-center justify-center gap-1.5 rounded-md font-sans text-xs font-medium transition duration-fast focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary";

export const PosterCardActions: React.FC<PosterCardActionsProps> = ({
  scenario,
}) => {
  const handlePlay = usePlayScenario(scenario.scenario_id);
  const { isSaved, isPending, handleToggleSave } = useSaveScenario(
    scenario.scenario_id,
  );

  return (
    <div className="pointer-events-none invisible absolute inset-x-0 bottom-0 flex gap-2 bg-linear-to-t from-surface via-surface/90 to-transparent p-3 pt-8 opacity-0 transition-opacity duration-fast group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100">
      <button
        type="button"
        onClick={handlePlay}
        className={`${ACTION_BUTTON_CLASSES} flex-1 bg-primary text-primary-contrast hover:bg-primary/90`}
      >
        <IconPlayerPlayFilled size={13} stroke={1.5} />
        Play
      </button>
      <button
        type="button"
        onClick={handleToggleSave}
        disabled={isPending}
        aria-pressed={isSaved}
        className={`${ACTION_BUTTON_CLASSES} border border-border-strong bg-surface-raised/80 px-3 text-content-muted hover:text-content`}
      >
        {isSaved ? <IconBookmarkFilled size={13} /> : <IconBookmark size={13} stroke={1.5} />}
        {isSaved ? "Saved" : "Save"}
      </button>
    </div>
  );
};

