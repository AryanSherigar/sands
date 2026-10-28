import React from "react";
import {
  GENTLE_WINDOW_WARNING_MS,
  MAX_WINDOW_MS,
  MIN_WINDOW_MS,
  MS_PER_SECOND,
} from "../../constants/ruleCheck";
import { WindowSliderProps } from "./WindowSlider.types";

export const WindowSlider: React.FC<WindowSliderProps> = ({
  seconds,
  onChange,
}) => {
  const isShort = seconds * MS_PER_SECOND < GENTLE_WINDOW_WARNING_MS;

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    onChange(Number(event.target.value));

  return (
    <div className="space-y-1">
      <label className="block text-sm text-content-muted">
        Window (seconds): {seconds}
        <input
          type="range"
          aria-label="Window (seconds)"
          min={MIN_WINDOW_MS / MS_PER_SECOND}
          max={MAX_WINDOW_MS / MS_PER_SECOND}
          step={1}
          value={seconds}
          onChange={handleChange}
          className="mt-1 block w-full"
        />
      </label>
      {isShort && (
        <p role="status" className="text-xs text-warning">
          Under 3 seconds is very hard to answer; consider a longer window.
        </p>
      )}
    </div>
  );
};
