import { apiClient } from "@/shared/lib/api-client";
import type { AchievementSummary } from "../types/achievement.types";

export const fetchMyAchievements = async (): Promise<AchievementSummary[]> => {
  const { data } = await apiClient.get<AchievementSummary[]>(
    "/v1/users/me/achievements",
  );
  return data;
};
