import React, { useState } from "react";
import {
  CHART_HEIGHT,
  CHART_LABEL_BASELINE,
  CHART_LABEL_GUTTER,
  CHART_WIDTH,
  TONE_FILL_CLASSES,
} from "../../constants/stats";
import { plotBars } from "../../lib/chartGeometry";
import { ChartGridlines } from "./ChartGridlines";
import { ChartTooltip } from "./ChartTooltip";
import type { SeriesChartProps } from "./chart.types";

export const Histogram: React.FC<SeriesChartProps> = ({ data, ariaLabel, tone }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const bars = plotBars(data);
  const activeBar = activeIndex === null ? undefined : bars[activeIndex];
  const handleEnter = (index: number) => (): void => setActiveIndex(index);
  const handleLeave = (): void => setActiveIndex(null);
  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-label={ariaLabel}
        className="h-48 w-full"
        onMouseLeave={handleLeave}
      >
        <ChartGridlines bottom={CHART_HEIGHT - CHART_LABEL_GUTTER} />
        {bars.map((bar, index) => (
          <g key={bar.datum.label} onMouseEnter={handleEnter(index)}>
            <rect
              x={bar.x}
              y={bar.y}
              width={bar.width}
              height={bar.height}
              rx={2}
              className={TONE_FILL_CLASSES[tone]}
            />
            <text
              x={bar.x + bar.width / 2}
              y={CHART_LABEL_BASELINE}
              textAnchor="middle"
              className="fill-content-muted font-mono text-[11px]"
            >
              {bar.datum.label}
            </text>
          </g>
        ))}
      </svg>
      {activeBar && <ChartTooltip datum={activeBar.datum} />}
    </div>
  );
};
