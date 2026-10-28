const MS_PER_MINUTE = 60_000;
const MINUTES_PER_HOUR = 60;
const HOURS_PER_DAY = 24;
const JUST_NOW_MAX_MINUTES = 1;
const RELATIVE_TIME_MAX_DAYS = 7;

export const formatRelativeTime = (isoTimestamp: string, now: Date): string => {
  const minutes = Math.floor(
    (now.getTime() - new Date(isoTimestamp).getTime()) / MS_PER_MINUTE,
  );
  if (minutes < JUST_NOW_MAX_MINUTES) return "just now";
  if (minutes < MINUTES_PER_HOUR) return `${minutes}m ago`;
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  if (hours < HOURS_PER_DAY) return `${hours}h ago`;
  const days = Math.floor(hours / HOURS_PER_DAY);
  if (days === 1) return "yesterday";
  if (days < RELATIVE_TIME_MAX_DAYS) return `${days}d ago`;
  return new Date(isoTimestamp).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};
