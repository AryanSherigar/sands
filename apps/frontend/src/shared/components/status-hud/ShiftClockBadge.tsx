import React from "react";
import { ShiftClockBadgeProps } from "./ShiftClockBadge.types";

export const ShiftClockBadge: React.FC<ShiftClockBadgeProps> = ({
  label,
  time,
  isGlitched = false,
  shouldAnimate = false,
}) => (
  <div
    role="group"
    aria-label={`${label} ${time}`}
    className="flex items-center gap-1.5 border border-inherit/20 px-2 py-1 font-mono text-xs"
  >
    <span className="opacity-60">{label}</span>
    <time
      data-glitched={isGlitched && shouldAnimate}
      className="clock-time tabular-nums font-semibold"
    >
      {time}
    </time>
  </div>
);
