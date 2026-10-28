import React from "react";
import { IconPlayerPlay, IconStarFilled } from "@tabler/icons-react";
import type { ScenarioPublishedMetricsProps } from "./StudioList.types";

const formatCount = (count: number): string => count.toLocaleString();

export const ScenarioPublishedMetrics: React.FC<
  ScenarioPublishedMetricsProps
> = ({ scenario }) => (
  <p className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-sm tabular-nums text-content-muted">
    <span className="inline-flex items-center gap-1">
      <IconPlayerPlay
        size={16}
        aria-hidden="true"
        className="text-content-faint"
      />
      {formatCount(scenario.play_count)}
      <span className="font-sans text-xs text-content-faint">plays</span>
    </span>
    <span className="inline-flex items-center gap-1">
      <IconStarFilled size={16} aria-hidden="true" className="text-warning" />
      {scenario.review_count === 0 ? (
        <span className="font-sans text-xs text-content-faint">
          No reviews yet
        </span>
      ) : (
        <>
          {Number(scenario.rating_avg).toFixed(1)}
          <span className="font-sans text-xs text-content-faint">
            ({formatCount(scenario.review_count)})
          </span>
        </>
      )}
    </span>
  </p>
);
