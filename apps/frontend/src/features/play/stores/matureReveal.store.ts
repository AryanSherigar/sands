import { create } from "zustand";

interface MatureRevealState {
  revealedScenarioIds: string[];
  reveal: (scenarioId: string) => void;
}

// NOTE: In-memory on purpose. "Show anyway" lasts for this visit only and
// never changes the saved show_mature preference.
export const useMatureRevealStore = create<MatureRevealState>((set) => ({
  revealedScenarioIds: [],
  reveal: (scenarioId) =>
    set((state) => ({
      revealedScenarioIds: [...state.revealedScenarioIds, scenarioId],
    })),
}));
