import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { fetchMyEndings } from "../api/profileApi";
import type { ProfileEndings } from "../types/endings.types";

const ANONYMOUS_KEY = "anonymous";

export const useProfileEndings = () => {
  const userId = useAuthStore((state) => state.user?.user_id);

  return useQuery<ProfileEndings, Error>({
    queryKey: ["profile-endings", userId ?? ANONYMOUS_KEY],
    queryFn: fetchMyEndings,
    staleTime: 0,
  });
};
