import React from "react";
import { isBlockingProblem } from "@/shared/lib/map-tracing/mapChecks";
import type { ProblemListProps } from "./RegionMapEditor.types";

export const ProblemList: React.FC<ProblemListProps> = ({
  problems,
  regionNameById,
  onSelectRegion,
}) => {
  const ordered = [...problems].sort(
    (first, second) => Number(isBlockingProblem(second)) - Number(isBlockingProblem(first)),
  );
  if (ordered.length === 0) {
    return <p className="text-sm text-content-muted">No problems found.</p>;
  }
  return (
    <ul aria-label="Problems" className="space-y-1">
      {ordered.map((problem) => {
        const label = problem.regionId ? (regionNameById[problem.regionId] ?? problem.regionId) : "Whole map";
        const tone = isBlockingProblem(problem) ? "text-content" : "text-content-muted";
        return (
          <li key={`${problem.regionId}-${problem.kind}`} className={`text-sm ${tone}`}>
            {problem.regionId ? (
              <button
                type="button"
                className="w-full rounded-sm px-2 py-1 text-left hover:bg-surface-overlay"
                onClick={() => onSelectRegion(problem.regionId as string)}
              >
                {label}: {problem.detail}
              </button>
            ) : (
              <span className="px-2 py-1">
                {label}: {problem.detail}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
};
