import React from "react";
import { MeterBarProps } from "./MeterBar.types";

const BAR_VIEWBOX_WIDTH = 100;
const BAR_VIEWBOX_HEIGHT = 4;
const TRACK_OPACITY = 0.2;

// The state may sit below `clampMin` (a sanity floor of -100, say); the bar
// never does.
const clampValue = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

export const MeterBar: React.FC<MeterBarProps> = ({
  label,
  value,
  clampMin,
  clampMax,
  tierName,
  shouldAnimate,
}) => {
  const shownValue = clampValue(value, clampMin, clampMax);
  const fillScale = (shownValue - clampMin) / (clampMax - clampMin);
  const valueText = tierName ? `${shownValue}, ${tierName}` : `${shownValue}`;

  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={clampMin}
      aria-valuemax={clampMax}
      aria-valuenow={shownValue}
      aria-valuetext={valueText}
      className="flex items-center gap-2 font-mono text-xs"
    >
      <span className="opacity-60">{label}</span>
      <svg
        aria-hidden="true"
        viewBox={`0 0 ${BAR_VIEWBOX_WIDTH} ${BAR_VIEWBOX_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-1.5 w-24 rounded-sm text-current"
      >
        <rect
          width={BAR_VIEWBOX_WIDTH}
          height={BAR_VIEWBOX_HEIGHT}
          fill="currentColor"
          fillOpacity={TRACK_OPACITY}
        />
        <rect
          width={BAR_VIEWBOX_WIDTH}
          height={BAR_VIEWBOX_HEIGHT}
          fill="currentColor"
          transform={`scale(${fillScale} 1)`}
          className={shouldAnimate ? "meter-fill-animated" : "transition-none"}
        />
      </svg>
      <span className="tabular-nums font-semibold">{shownValue}</span>
      {tierName ? <span className="opacity-70">{tierName}</span> : null}
    </div>
  );
};
