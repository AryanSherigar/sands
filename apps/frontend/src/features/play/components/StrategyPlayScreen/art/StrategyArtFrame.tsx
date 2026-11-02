import React from "react";
import type { StrategyArtFrameProps } from "./StrategyArtFrame.types";

export const StrategyArtFrame: React.FC<StrategyArtFrameProps> = ({
  artUrl,
  isLoading,
  altText,
  hasFailed = false,
  canRetry = true,
  onRetry,
}) => {
  if (artUrl) {
    return (
      <img
        src={artUrl}
        alt={altText}
        className="strategy-fade w-full aspect-[16/9] object-cover rounded-lg border border-on-surface/15 shadow-sm"
      />
    );
  }
  if (hasFailed) {
    return (
      <div
        role="alert"
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-on-surface/10 bg-surface-dim px-3 py-2 text-xs text-on-surface/70"
      >
        <span>The illustration could not be painted.</span>
        {canRetry && onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="font-semibold underline hover:text-on-surface"
          >
            Try again
          </button>
        ) : null}
      </div>
    );
  }
  if (!isLoading) return null;
  return (
    <div
      role="status"
      aria-label="Painting the scene"
      className="w-full aspect-[16/9] rounded-lg border border-on-surface/10 bg-surface-dim motion-safe:animate-pulse"
    />
  );
};
