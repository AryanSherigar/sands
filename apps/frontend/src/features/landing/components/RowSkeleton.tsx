import React from "react";
import { SKELETON_CARD_COUNT } from "../constants/landing.constants";

const SKELETON_KEYS = Array.from(
  { length: SKELETON_CARD_COUNT },
  (_, index) => `skeleton-card-${index}`,
);

export const RowSkeleton: React.FC = () => (
  <div aria-hidden="true" className="space-y-3">
    <div className="mx-4 h-6 w-32 animate-pulse rounded-sm bg-surface-raised md:mx-14" />
    <div className="flex gap-3 overflow-hidden px-4 md:px-14">
      {SKELETON_KEYS.map((key) => (
        <div
          key={key}
          className="aspect-video w-[85vw] shrink-0 animate-pulse rounded-md bg-surface-raised sm:w-80 lg:w-104"
        />
      ))}
    </div>
  </div>
);
