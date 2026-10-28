const CLOCK_PATTERN =
  /^(?<hour>\d{1,2})(?:[:.\s]?(?<minute>\d{2}))?\s*(?<meridiem>[ap])?\.?(?:m\.?)?$/;
const MINUTES_PER_HOUR = 60;
const MINUTES_PER_HALF_DAY = 720;
const HOURS_PER_HALF_DAY = 12;
const HOURS_PER_DAY = 24;
const PM_MARKER = "p";

const withMeridiem = (
  hour: number,
  minute: number,
  isPm: boolean,
): number[] => {
  if (hour < 1 || hour > HOURS_PER_HALF_DAY) return [];
  const base = (hour % HOURS_PER_HALF_DAY) * MINUTES_PER_HOUR + minute;
  return [base + (isPm ? MINUTES_PER_HALF_DAY : 0)];
};

const withoutMeridiem = (hour: number, minute: number): number[] => {
  if (hour >= HOURS_PER_DAY) return [];
  if (hour < 1 || hour > HOURS_PER_HALF_DAY) {
    return [hour * MINUTES_PER_HOUR + minute];
  }
  const face = (hour % HOURS_PER_HALF_DAY) * MINUTES_PER_HOUR + minute;
  return [face, face + MINUTES_PER_HALF_DAY];
};

export const parseClockText = (text: string): number[] => {
  const groups = CLOCK_PATTERN.exec(text.trim().toLowerCase())?.groups;
  if (!groups) return [];
  const hour = Number(groups.hour);
  const minute = Number(groups.minute ?? 0);
  if (minute >= MINUTES_PER_HOUR) return [];
  const result = groups.meridiem
    ? withMeridiem(hour, minute, groups.meridiem === PM_MARKER)
    : withoutMeridiem(hour, minute);
  return [...new Set(result)].sort((a, b) => a - b);
};
