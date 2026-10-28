import { ClockFormat } from "@/shared/types/display-hints.types";

const MINUTES_PER_HOUR = 60;
const MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR;
const NOON_HOUR = 12;
const START_PATTERN = /^(\d{2}):(\d{2})$/;

const startMinutesOf = (start: string): number => {
  const match = START_PATTERN.exec(start);
  if (!match) return 0;
  return Number(match[1]) * MINUTES_PER_HOUR + Number(match[2]);
};

const pad = (value: number): string => String(value).padStart(2, "0");

// Minutes since the scenario's start time, shown as a time of day. Wraps past
// midnight in either direction. `glitchMinute` replaces the minute digits with
// an impossible value (60-99) for the clock's glitch effect.
export function formatClock(
  minutesSinceStart: number,
  start: string,
  format: ClockFormat,
  glitchMinute?: number,
): string {
  const total = startMinutesOf(start) + Math.floor(minutesSinceStart);
  const timeOfDay =
    ((total % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  const hour = Math.floor(timeOfDay / MINUTES_PER_HOUR);
  const minute = glitchMinute ?? timeOfDay % MINUTES_PER_HOUR;
  if (format === "24h") return `${pad(hour)}:${pad(minute)}`;
  const hour12 = hour % NOON_HOUR === 0 ? NOON_HOUR : hour % NOON_HOUR;
  const suffix = hour < NOON_HOUR ? "AM" : "PM";
  return `${pad(hour12)}:${pad(minute)} ${suffix}`;
}
