import { WEEKDAY_NAMES } from "../constants/overview.constants";

const joinWithAnd = (names: string[]): string => {
  if (names.length === 1) return names[0];
  const head = names.slice(0, -1).join(", ");
  return `${head} and ${names[names.length - 1]}`;
};

export const formatPlayedDaysText = (playedDays: boolean[]): string => {
  const names = WEEKDAY_NAMES.filter((_, index) => playedDays[index]);
  if (names.length === 0) return "No stories this week yet.";
  return `Played on ${joinWithAnd(names)} this week.`;
};

export const formatWeeklyCaption = (count: number): string => {
  if (count === 0) return "No stories this week yet";
  return `Played ${count} ${count === 1 ? "day" : "days"} this week`;
};
