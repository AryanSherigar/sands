import React from "react";

const SKELETON_BLOCK_COUNT = 3;

export const TabSkeleton: React.FC = () => (
  <div
    role="status"
    aria-busy="true"
    aria-label="Loading"
    className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
  >
    {Array.from({ length: SKELETON_BLOCK_COUNT }, (_, i) => (
      <div
        key={i}
        className="h-56 animate-pulse rounded-md border border-border-subtle bg-surface-raised motion-reduce:animate-none"
      />
    ))}
  </div>
);
