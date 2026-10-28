import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { TAB_EMPTY_COPY } from "../../constants/studio-list";
import type { StudioEmptyStateProps } from "./StudioList.types";

const EMPTY_BOX_CLASSES =
  "flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center";

export const StudioEmptyState: React.FC<StudioEmptyStateProps> = ({
  tab,
  query,
  hasAnyScenarios,
  onClearQuery,
  onNewScenario,
}) => {
  if (query) {
    return (
      <div className={EMPTY_BOX_CLASSES}>
        <p className="font-sans text-content-muted">No worlds match “{query}”</p>
        <Button variant="secondary" onClick={onClearQuery}>
          Clear search
        </Button>
      </div>
    );
  }
  if (hasAnyScenarios && tab !== "all") {
    return (
      <div className={EMPTY_BOX_CLASSES}>
        <p className="font-sans text-content-muted">{TAB_EMPTY_COPY[tab]}</p>
      </div>
    );
  }
  return (
    <div className={EMPTY_BOX_CLASSES}>
      <h2 className="font-display text-xl font-semibold text-content">
        Create your first story
      </h2>
      <p className="font-sans text-sm text-content-muted">
        Simple mode gets you publishing in minutes.
      </p>
      <Button variant="primary" onClick={onNewScenario}>
        New Story
      </Button>
    </div>
  );
};
