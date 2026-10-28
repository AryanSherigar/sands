import { formatRelativeTime } from "@/shared/lib/formatRelativeTime";
import { MAX_GENRES_IN_SUBTEXT } from "../constants/overview.constants";

export { formatRelativeTime };

const PERCENT_MULTIPLIER = 100;
const PERCENT_FRACTION_DIGITS = 1;

export const formatEndingsCompletion = (
  found: number,
  total: number,
): string => {
  if (total === 0) return "No endings yet";
  const percent = ((found / total) * PERCENT_MULTIPLIER).toFixed(
    PERCENT_FRACTION_DIGITS,
  );
  return `${percent}% completion`;
};

export const formatGenresSubtext = (genres: string[]): string => {
  if (genres.length === 0) return "None yet";
  const shown = genres.slice(0, MAX_GENRES_IN_SUBTEXT).join(", ");
  const remaining = genres.length - MAX_GENRES_IN_SUBTEXT;
  return remaining > 0 ? `${shown} +${remaining}` : shown;
};

export const formatContinueSubtitle = (
  genre: string | null,
  mode: "newbie" | "master",
): string => {
  const modeLabel = `${mode} mode`;
  return (genre ? `${genre} · ${modeLabel}` : modeLabel).toUpperCase();
};
