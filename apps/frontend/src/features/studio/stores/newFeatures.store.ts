import { create } from "zustand";
import { FEATURE_HIGHLIGHT_MS } from "../constants/newFeatures";

interface NewFeaturesState {
  unseenFeatureIds: string[];
  highlightedFeatureId: string | null;
  setUnseenFeatureIds: (featureIds: string[]) => void;
  highlightFeature: (featureId: string) => void;
}

let highlightTimer: ReturnType<typeof setTimeout> | null = null;

export const useNewFeaturesStore = create<NewFeaturesState>((set) => ({
  unseenFeatureIds: [],
  highlightedFeatureId: null,
  setUnseenFeatureIds: (featureIds) => set({ unseenFeatureIds: featureIds }),
  highlightFeature: (featureId) => {
    if (highlightTimer) clearTimeout(highlightTimer);
    set({ highlightedFeatureId: featureId });
    highlightTimer = setTimeout(() => {
      set({ highlightedFeatureId: null });
      highlightTimer = null;
    }, FEATURE_HIGHLIGHT_MS);
  },
}));
