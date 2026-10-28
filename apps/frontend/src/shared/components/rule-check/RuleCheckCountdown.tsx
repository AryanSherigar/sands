import React from "react";
import { RuleCheckCountdownProps } from "./RuleCheckCountdown.types";

const MS_PER_SECOND = 1000;
const UNTIMED_LABEL = "Take your time";
const LOCKED_LABEL = "Read on\u2026";

const secondsLabel = (remainingMs: number): string => {
  const seconds = Math.ceil(remainingMs / MS_PER_SECOND);
  return `${seconds} ${seconds === 1 ? "second" : "seconds"} remaining`;
};

export const RuleCheckCountdown: React.FC<RuleCheckCountdownProps> = ({
  remainingMs,
  windowMs,
  isUntimed = false,
  isLocked = false,
}) => {
  if (isLocked) {
    return <p className="text-xs text-content-faint">{LOCKED_LABEL}</p>;
  }
  if (isUntimed) {
    return <p className="text-xs text-content-faint">{UNTIMED_LABEL}</p>;
  }
  return (
    <>
      <progress
        aria-label="Time remaining"
        aria-valuemin={0}
        aria-valuemax={windowMs}
        aria-valuenow={remainingMs}
        value={remainingMs}
        max={windowMs}
        className="h-1.5 w-full appearance-none [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-surface-inset [&::-webkit-progress-value]:bg-accent"
      />
      <p aria-live="polite" className="text-xs text-content-faint">
        {secondsLabel(remainingMs)}
      </p>
    </>
  );
};
