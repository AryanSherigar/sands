import React from "react";
import type { SectionErrorProps } from "./SectionError.types";

export const SectionError: React.FC<SectionErrorProps> = ({
  label,
  onRetry,
}) => (
  <div
    role="alert"
    className="flex items-center justify-between gap-3 rounded-md border border-border-subtle bg-surface-raised px-4 py-3 font-sans text-sm text-content-muted"
  >
    <span>Couldn&apos;t load {label}</span>
    <button
      type="button"
      onClick={onRetry}
      className="font-semibold text-accent hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      Retry
    </button>
  </div>
);
