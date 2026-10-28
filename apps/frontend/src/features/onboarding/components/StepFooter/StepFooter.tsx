import React from "react";
import { IconArrowRight } from "@tabler/icons-react";
import type { StepFooterProps } from "./StepFooter.types";

export const StepFooter: React.FC<StepFooterProps> = ({
  onNext,
  nextLabel = "Next",
  isNextDisabled = false,
  isBusy = false,
  onBack,
  onSkip,
}) => (
  <div className="sticky bottom-0 z-10 mt-8 flex items-center justify-between border-t border-border-subtle bg-surface/95 pt-4 pb-2 backdrop-blur-xs md:static md:bg-transparent md:backdrop-blur-none">
    <div>
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          disabled={isBusy}
          className="rounded-md px-4 py-2 text-sm font-medium text-content-muted transition-colors hover:bg-white/6 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-40"
        >
          Back
        </button>
      )}
    </div>
    <div className="flex items-center gap-3">
      {onSkip && (
        <button
          type="button"
          onClick={onSkip}
          disabled={isBusy}
          className="rounded-md px-4 py-2 text-sm font-medium text-content-muted transition-colors hover:bg-white/6 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-40"
        >
          Skip
        </button>
      )}
      <button
        type="button"
        onClick={onNext}
        disabled={isNextDisabled || isBusy}
        aria-label={isBusy ? "Saving..." : nextLabel}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-contrast transition-opacity hover:opacity-95 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-content active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
      >
        <span>{isBusy ? "Saving..." : nextLabel}</span>
        {!isBusy && <IconArrowRight size={16} aria-hidden="true" />}
      </button>
    </div>
  </div>
);
