import React from "react";
import type { ScenarioRowSkeletonListProps } from "./StudioList.types";

export const ScenarioRowSkeletonList: React.FC<
  ScenarioRowSkeletonListProps
> = ({ count }) => (
  <>
    {Array.from({ length: count }, (_, index) => (
      <li
        key={index}
        aria-hidden="true"
        className="h-32 rounded-md border border-border-subtle bg-surface-raised motion-safe:animate-pulse"
      />
    ))}
  </>
);
