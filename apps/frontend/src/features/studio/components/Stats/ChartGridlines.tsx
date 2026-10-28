import React from "react";
import { CHART_PADDING, CHART_WIDTH } from "../../constants/stats";
import { gridlineOffsets } from "../../lib/chartGeometry";
import type { ChartGridlinesProps } from "./ChartGridlines.types";

export const ChartGridlines: React.FC<ChartGridlinesProps> = ({ bottom }) => (
  <g aria-hidden="true">
    {gridlineOffsets(bottom).map((offset) => (
      <line
        key={offset}
        x1={CHART_PADDING}
        x2={CHART_WIDTH - CHART_PADDING}
        y1={offset}
        y2={offset}
        strokeWidth={1}
        className="stroke-border-subtle"
      />
    ))}
  </g>
);
