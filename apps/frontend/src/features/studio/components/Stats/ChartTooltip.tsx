import React from "react";
import { formatCount } from "../../lib/statsFormat";
import type { ChartTooltipProps } from "./ChartTooltip.types";

export const ChartTooltip: React.FC<ChartTooltipProps> = ({ datum }) => (
  <div
    aria-hidden="true"
    className="pointer-events-none absolute right-2 top-2 rounded-md border border-border-subtle bg-surface-overlay px-2 py-1 font-mono text-xs tabular-nums text-content"
  >
    {datum.label}: {formatCount(datum.value)}
  </div>
);
