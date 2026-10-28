import { create } from "zustand";
import type { SignInTrigger } from "@/shared/constants/sign-in-triggers";

interface SignInModalState {
  trigger: SignInTrigger | null;
  resolvePending: ((isSignedIn: boolean) => void) | null;
  open: (trigger: SignInTrigger) => Promise<boolean>;
  settle: (isSignedIn: boolean) => void;
}

export const useSignInModalStore = create<SignInModalState>((set, get) => ({
  trigger: null,
  resolvePending: null,
  open: (trigger) => {
    get().resolvePending?.(false);
    return new Promise<boolean>((resolve) => {
      set({ trigger, resolvePending: resolve });
    });
  },
  settle: (isSignedIn) => {
    get().resolvePending?.(isSignedIn);
    set({ trigger: null, resolvePending: null });
  },
}));
