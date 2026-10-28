import { create } from "zustand";

interface AtmosphereState {
  flickerNonce: number;
  triggerFlicker: () => void;
}

// UI-only: each trigger asks the reader to flicker once. The reader watches the
// nonce rather than a boolean so back-to-back triggers each count.
export const useAtmosphereStore = create<AtmosphereState>((set) => ({
  flickerNonce: 0,
  triggerFlicker: () => set((s) => ({ flickerNonce: s.flickerNonce + 1 })),
}));
