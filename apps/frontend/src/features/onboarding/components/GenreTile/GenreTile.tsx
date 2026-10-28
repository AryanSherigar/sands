import React from "react";
import { DEFAULT_GENRE_COLOR, GENRE_COLORS } from "@/shared/constants/genres";
import { GENRE_METADATA } from "../../constants/onboarding.constants";
import type { GenreTileProps } from "./GenreTile.types";

export const GenreTile: React.FC<GenreTileProps> = ({
  genre,
  isSelected,
  isDisabled,
  onToggle,
  subtitle,
  storyPreview,
  accentColor,
}) => {
  const meta = GENRE_METADATA[genre];
  const color =
    accentColor ?? meta?.color ?? GENRE_COLORS[genre] ?? DEFAULT_GENRE_COLOR;
  const desc = subtitle ?? meta?.subtitle;
  const preview = storyPreview ?? meta?.storyPreview;
  const isBlocked = isDisabled && !isSelected;

  const containerClasses = isSelected
    ? "border-content bg-surface-overlay"
    : "border-border-subtle bg-surface-raised hover:border-border-strong";

  return (
    <label
      className={`group relative flex h-28 cursor-pointer flex-col justify-between overflow-hidden rounded-lg border p-4 text-left transition-all duration-fast ${containerClasses} ${
        isBlocked ? "cursor-not-allowed opacity-40" : ""
      }`}
    >
      <input
        type="checkbox"
        aria-label={genre}
        checked={isSelected}
        disabled={isBlocked}
        onChange={() => onToggle(genre)}
        className="sr-only"
      />
      {/* 4px Top accent bar */}
      <div
        className="absolute inset-x-0 top-0 h-1"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />

      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <span className="block truncate font-display text-sm font-semibold text-content">
            {genre}
          </span>
          {desc && (
            <span className="mt-0.5 block truncate text-xs text-content-faint">
              {desc}
            </span>
          )}
        </div>

        {/* Checkbox indicator */}
        <div
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors ${
            isSelected
              ? "border-content bg-content text-primary-contrast"
              : "border-border-strong bg-surface-inset text-transparent"
          }`}
          aria-hidden="true"
        >
          {isSelected && (
            <svg
              className="h-3.5 w-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <path
                d="M5 13l4 4L19 7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Story preview footer */}
      {preview && (
        <div className="flex items-center gap-2 font-mono text-[11px] text-content-faint">
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
          <span className="truncate">{preview}</span>
        </div>
      )}
    </label>
  );
};
