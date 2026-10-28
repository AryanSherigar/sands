import React, { useState } from "react";
import {
  CHART_HEIGHT,
  CHART_PADDING,
  CHART_POINT_RADIUS,
  CHART_WIDTH,
  TONE_FILL_CLASSES,
  TONE_STROKE_CLASSES,
} from "../../constants/stats";
import { plotPoints } from "../../lib/chartGeometry";
import { ChartGridlines } from "./ChartGridlines";
import { ChartTooltip } from "./ChartTooltip";
import type { SeriesChartProps } from "./chart.types";

export const LineChart: React.FC<SeriesChartProps> = ({ data, ariaLabel, tone }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const points = plotPoints(data);
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
  const activePoint = activeIndex === null ? undefined : points[activeIndex];
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
        <ChartGridlines bottom={CHART_HEIGHT - CHART_PADDING} />
        <polyline
          points={polyline}
          fill="none"
          strokeWidth={2}
          className={TONE_STROKE_CLASSES[tone]}
        />
        {points.map((point, index) => (
          <circle
            key={point.datum.label}
            cx={point.x}
            cy={point.y}
            r={CHART_POINT_RADIUS}
            className={TONE_FILL_CLASSES[tone]}
            onMouseEnter={handleEnter(index)}
          />
        ))}
      </svg>
      {activePoint && <ChartTooltip datum={activePoint.datum} />}
    </div>
  );
};
