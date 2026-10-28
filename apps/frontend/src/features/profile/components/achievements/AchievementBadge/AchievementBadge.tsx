import React, { useState } from "react";
import { getAchievementIcon } from "../../../constants/achievementIcons.constants";
import { PROGRESS_WIDTH_CLASSES } from "../../../constants/achievements.constants";
import {
  formatEarnedDate,
  formatProgress,
  getProgressWidthClass,
} from "../../../lib/achievements";
import type { AchievementBadgeProps } from "./AchievementBadge.types";

const FRAME_BASE_CLASSES =
  "flex h-16 w-16 items-center justify-center rounded-full bg-surface-raised";
const FRAME_EARNED_CLASSES = "border border-content text-content";
const FRAME_LOCKED_CLASSES =
  "border border-dashed border-border-strong text-content-faint";

export const AchievementBadge: React.FC<AchievementBadgeProps> = ({ item }) => {
  const [isOpen, setIsOpen] = useState(false);
  const Glyph = getAchievementIcon(item.key);
  const isEarned = item.earned_at !== null;

  return (
    <li className="flex flex-col items-center gap-2 text-center">
      <button
        type="button"
        aria-expanded={isOpen}
        aria-label={`${item.name}, ${isEarned ? "earned" : "not yet earned"}`}
        onClick={() => setIsOpen((current) => !current)}
        className="flex flex-col items-center gap-2 rounded-md p-1 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        <span
          className={`${FRAME_BASE_CLASSES} ${isEarned ? FRAME_EARNED_CLASSES : FRAME_LOCKED_CLASSES}`}
        >
          <Glyph size={32} stroke={1.5} aria-hidden="true" />
        </span>
        <span className="text-sm font-medium text-content">{item.name}</span>
        <span className="text-xs text-content-faint">{item.family}</span>
      </button>
      {item.earned_at && (
        <p className="font-mono text-xs text-content-muted">
          {formatEarnedDate(item.earned_at)}
        </p>
      )}
      {!isEarned && item.progress && (
        <div className="w-full space-y-1">
          <div
            role="progressbar"
            aria-label={item.name}
            aria-valuenow={item.progress.current}
            aria-valuemin={0}
            aria-valuemax={item.progress.target}
            className="h-1.5 w-full overflow-hidden rounded-full bg-surface-inset"
          >
            <div
              className={`h-full bg-content ${getProgressWidthClass(item.progress, PROGRESS_WIDTH_CLASSES)}`}
            />
          </div>
          <p className="font-mono text-xs text-content-muted">
            {formatProgress(item.progress)}
          </p>
        </div>
      )}
      {isOpen && <p className="text-xs text-content-muted">{item.requirement}</p>}
    </li>
  );
};
