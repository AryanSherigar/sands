import React from "react";
import { BAR_LIST_ROW_HEIGHT, CHART_WIDTH } from "../../constants/stats";
import { BarListRow } from "./BarListRow";
import type { BarListProps } from "./chart.types";

export const BarList: React.FC<BarListProps> = ({ items, ariaLabel, tone }) => (
  <svg
    viewBox={`0 0 ${CHART_WIDTH} ${items.length * BAR_LIST_ROW_HEIGHT}`}
    role="img"
    aria-label={ariaLabel}
    className="w-full"
  >
    {items.map((item, index) => (
      <BarListRow
        key={item.label}
        item={item}
        top={index * BAR_LIST_ROW_HEIGHT}
        tone={tone}
      />
    ))}
  </svg>
);
