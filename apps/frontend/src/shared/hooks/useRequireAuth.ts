import { useCallback } from "react";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { SignInTrigger } from "@/shared/constants/sign-in-triggers";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";

export const useRequireAuth = (trigger: SignInTrigger) => {
  const openSignInModal = useSignInModalStore((state) => state.open);

  return useCallback((): Promise<boolean> => {
    if (useAuthStore.getState().isAuthenticated) return Promise.resolve(true);
    return openSignInModal(trigger);
  }, [openSignInModal, trigger]);
};
