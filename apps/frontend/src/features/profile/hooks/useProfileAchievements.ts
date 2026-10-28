import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import {
  fetchMyAchievements,
  fetchPublicAchievements,
} from "../api/profileApi";
import type { AchievementItem } from "../types/achievements.types";

const ANONYMOUS_KEY = "anonymous";

export const useProfileAchievements = (
  userId: string,
  isOwnerData: boolean,
) => {
  const authUserId = useAuthStore((state) => state.user?.user_id);

  return useQuery<AchievementItem[], Error>({
    queryKey: isOwnerData
      ? ["profile-achievements", "owner", authUserId ?? ANONYMOUS_KEY]
      : ["profile-achievements", "public", userId],
    queryFn: () =>
      isOwnerData ? fetchMyAchievements() : fetchPublicAchievements(userId),
    staleTime: 0,
  });
};
