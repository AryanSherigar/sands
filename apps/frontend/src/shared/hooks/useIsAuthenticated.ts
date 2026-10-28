import { useAuthStore } from "@/features/auth/stores/auth.store";

export const useIsAuthenticated = (): boolean =>
  useAuthStore((state) => state.isAuthenticated);
