import { WORLDMAKER_ACHIEVEMENT_KEY } from "../constants/achievements";
import type { AchievementSummary } from "../types/achievement.types";

export const findWorldmaker = (
  achievements: AchievementSummary[],
): AchievementSummary | null =>
  achievements.find((item) => item.key === WORLDMAKER_ACHIEVEMENT_KEY) ?? null;

export const isEarned = (achievement: AchievementSummary | null): boolean =>
  Boolean(achievement?.earned_at);
