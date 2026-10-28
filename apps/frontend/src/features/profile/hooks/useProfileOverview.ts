import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { fetchMyOverview } from "../api/profileApi";
import type { ProfileOverview } from "../types/overview.types";

const ANONYMOUS_KEY = "anonymous";

export const useProfileOverview = () => {
  const userId = useAuthStore((state) => state.user?.user_id);

  return useQuery<ProfileOverview, Error>({
    queryKey: ["profile-overview", userId ?? ANONYMOUS_KEY],
    queryFn: fetchMyOverview,
    staleTime: 0,
  });
};
