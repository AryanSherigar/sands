import { create } from "zustand";

interface OnboardingPromptState {
  shouldPromptAfterPause: boolean;
  requestPromptAfterPause: () => void;
  clearPrompt: () => void;
}

export const useOnboardingPromptStore = create<OnboardingPromptState>(
  (set) => ({
    shouldPromptAfterPause: false,
    requestPromptAfterPause: () => set({ shouldPromptAfterPause: true }),
    clearPrompt: () => set({ shouldPromptAfterPause: false }),
  }),
);
