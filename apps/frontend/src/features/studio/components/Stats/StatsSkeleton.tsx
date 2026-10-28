import React from "react";
import { SKELETON_TILE_COUNT } from "../../constants/stats";

const SKELETON_BLOCK =
  "animate-pulse rounded-lg bg-surface-raised motion-reduce:animate-none";

export const StatsSkeleton: React.FC = () => (
  <div aria-busy="true" aria-label="Loading stats" className="flex flex-col gap-8">
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: SKELETON_TILE_COUNT }, (_, index) => (
        <div key={index} className={`h-28 ${SKELETON_BLOCK}`} />
      ))}
    </div>
    <div className={`h-56 ${SKELETON_BLOCK}`} />
  </div>
);
