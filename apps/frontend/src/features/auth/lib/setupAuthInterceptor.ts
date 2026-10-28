import { setupApiClientAuth } from "@/shared/lib/api-client";
import { useAuthStore } from "../stores/auth.store";
import { refreshAccessToken } from "../api/auth.api";
import { UserResponse } from "../types/auth.types";
import { markSuspendedIfRefused } from "./accountSuspension";

export const initializeAuthInterceptors = (): void => {
  setupApiClientAuth({
    getAccessToken: () => useAuthStore.getState().accessToken,
    refreshAccessToken: async () => {
      try {
        const response = await refreshAccessToken();
        return {
          access_token: response.access_token,
          user: response.user,
        };
      } catch (error) {
        markSuspendedIfRefused(error);
        throw error;
      }
    },
    onAuthRefreshed: (token: string, user: unknown) => {
      useAuthStore.getState().setAuth(token, user as UserResponse);
    },
    onAuthFailed: () => {
      useAuthStore.getState().logout();
    },
  });
};
