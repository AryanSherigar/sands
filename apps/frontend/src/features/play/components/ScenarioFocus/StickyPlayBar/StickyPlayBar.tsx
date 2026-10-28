import React from "react";
import { PlayAction } from "../HeroActions/PlayAction";
import type { StickyPlayBarProps } from "./StickyPlayBar.types";

export const StickyPlayBar: React.FC<StickyPlayBarProps> = ({
  scenarioId,
  isDraft,
  isStartingPlaytest,
  onPlaytest,
}) => (
  <div className="fixed inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] z-30 animate-fade-in border-t border-border-subtle bg-surface-raised/95 p-3 backdrop-blur-sm lg:hidden">
    <PlayAction
      scenarioId={scenarioId}
      isDraft={isDraft}
      isStartingPlaytest={isStartingPlaytest}
      onPlaytest={onPlaytest}
    />
  </div>
);
