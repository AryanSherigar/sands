import { ACHIEVEMENT_FAMILY_ORDER } from "../constants/achievements.constants";
import type {
  AchievementItem,
  AchievementProgress,
} from "../types/achievements.types";

export interface AchievementFamilyGroup {
  family: string;
  items: AchievementItem[];
}

export const groupByFamily = (
  items: AchievementItem[],
): AchievementFamilyGroup[] =>
  ACHIEVEMENT_FAMILY_ORDER.map((family) => ({
    family,
    items: items.filter((item) => item.family === family),
  })).filter((group) => group.items.length > 0);

export const visibleAchievements = (
  items: AchievementItem[],
  isProgressVisible: boolean,
): AchievementItem[] =>
  isProgressVisible
    ? items
    : items
        .filter((item) => item.earned_at !== null)
        .map((item) => ({ ...item, progress: null }));

export const formatProgress = (progress: AchievementProgress): string =>
  `${progress.current.toLocaleString()} / ${progress.target.toLocaleString()}`;

export const formatEarnedDate = (isoTimestamp: string): string =>
  `Earned ${new Date(isoTimestamp).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  })}`;

export const getProgressWidthClass = (
  progress: AchievementProgress,
  widthClasses: readonly string[],
): string => {
  const lastStep = widthClasses.length - 1;
  const ratio = progress.target > 0 ? progress.current / progress.target : 0;
  const step = Math.min(lastStep, Math.max(0, Math.round(ratio * lastStep)));
  return widthClasses[step];
};
