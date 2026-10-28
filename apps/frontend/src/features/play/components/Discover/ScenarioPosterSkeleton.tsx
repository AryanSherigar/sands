import React from "react";

export const ScenarioPosterSkeleton: React.FC = () => (
  <div aria-hidden="true" className="flex animate-pulse flex-col gap-2 p-2">
    <div className="aspect-3/4 w-full rounded-lg bg-surface-inset" />
    <div className="h-4 w-3/4 rounded bg-surface-inset" />
    <div className="h-3 w-1/2 rounded bg-surface-inset" />
  </div>
);
