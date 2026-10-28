import React from "react";

export const ScenarioRowSkeleton: React.FC = () => (
  <div
    aria-hidden="true"
    className="flex animate-pulse flex-col gap-4 rounded-xl border border-border-subtle bg-surface-raised p-3.5 md:flex-row lg:gap-5 lg:p-4"
  >
    <div className="aspect-video w-full shrink-0 rounded-lg bg-surface-inset md:w-[280px] lg:w-[300px]" />
    <div className="flex flex-1 flex-col gap-3">
      <div className="h-6 w-2/3 rounded bg-surface-inset" />
      <div className="h-4 w-1/4 rounded bg-surface-inset" />
      <div className="h-4 w-full rounded bg-surface-inset" />
      <div className="h-4 w-1/2 rounded bg-surface-inset" />
    </div>
  </div>
);
