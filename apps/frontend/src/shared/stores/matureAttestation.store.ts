import { create } from "zustand";

interface MatureAttestationState {
  isOpen: boolean;
  resolvePending: ((isConfirmed: boolean) => void) | null;
  request: () => Promise<boolean>;
  settle: (isConfirmed: boolean) => void;
}

export const useMatureAttestationStore = create<MatureAttestationState>(
  (set, get) => ({
    isOpen: false,
    resolvePending: null,
    request: () => {
      get().resolvePending?.(false);
      return new Promise<boolean>((resolve) => {
        set({ isOpen: true, resolvePending: resolve });
      });
    },
    settle: (isConfirmed) => {
      get().resolvePending?.(isConfirmed);
      set({ isOpen: false, resolvePending: null });
    },
  }),
);
