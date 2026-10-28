import React from "react";
import { formatTrend, trendToneClass } from "../../lib/statsFormat";
import type { TrendLabelProps } from "./TrendLabel.types";

export const TrendLabel: React.FC<TrendLabelProps> = ({ trend, range }) => {
  if (trend === null) return null;
  const text = formatTrend(trend, range);
  if (text === null) return null;
  return (
    <span className={`font-mono text-xs tabular-nums ${trendToneClass(trend)}`}>
      {text}
    </span>
  );
};
