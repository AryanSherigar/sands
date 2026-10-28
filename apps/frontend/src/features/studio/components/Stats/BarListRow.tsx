import React from "react";
import {
  BAR_LIST_BAR_HEIGHT,
  BAR_LIST_LABEL_WIDTH,
  BAR_LIST_ROW_HEIGHT,
  CHART_WIDTH,
  TONE_FILL_CLASSES,
} from "../../constants/stats";
import { barListWidth } from "../../lib/chartGeometry";
import type { BarListRowProps } from "./chart.types";

export const BarListRow: React.FC<BarListRowProps> = ({ item, top, tone }) => {
  const middle = top + BAR_LIST_ROW_HEIGHT / 2;
  return (
    <g>
      <text
        x={0}
        y={middle}
        dominantBaseline="middle"
        className="fill-content-muted font-sans text-[13px]"
      >
        {item.label}
      </text>
      <rect
        x={BAR_LIST_LABEL_WIDTH}
        y={middle - BAR_LIST_BAR_HEIGHT / 2}
        width={barListWidth(item.fraction)}
        height={BAR_LIST_BAR_HEIGHT}
        rx={2}
        className={TONE_FILL_CLASSES[tone]}
      />
      <text
        x={CHART_WIDTH}
        y={middle}
        dominantBaseline="middle"
        textAnchor="end"
        className="fill-content font-mono text-[13px] tabular-nums"
      >
        {item.valueLabel}
      </text>
    </g>
  );
};
