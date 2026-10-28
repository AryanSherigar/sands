import React from "react";

const PARAGRAPH_SKELETON_KEYS = ["first", "second", "third"];

export const ScenarioLoadingSkeleton: React.FC = () => (
  <div
    role="status"
    aria-label="Loading scenario"
    className="mx-auto max-w-[1200px] animate-pulse space-y-8 px-4 pt-6 md:px-10"
  >
    <div className="h-72 rounded-md bg-surface-raised lg:h-[420px]" />
    <div className="space-y-3">
      {PARAGRAPH_SKELETON_KEYS.map((key) => (
        <div key={key} className="h-4 w-full rounded-sm bg-surface-raised" />
      ))}
    </div>
  </div>
);
