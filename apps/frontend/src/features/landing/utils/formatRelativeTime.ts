import { RELATIVE_TIME_UNITS } from "../constants/landing.constants";

const relativeTimeFormat = new Intl.RelativeTimeFormat("en", {
  numeric: "auto",
});

export const formatRelativeTime = (
  isoTimestamp: string,
  now: number = Date.now(),
): string => {
  const elapsed = new Date(isoTimestamp).getTime() - now;
  const match = RELATIVE_TIME_UNITS.find(
    ({ milliseconds }) => Math.abs(elapsed) >= milliseconds,
  );
  if (!match) return "just now";
  return relativeTimeFormat.format(
    Math.round(elapsed / match.milliseconds),
    match.unit,
  );
};
