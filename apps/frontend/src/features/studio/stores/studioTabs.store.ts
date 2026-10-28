import { create } from "zustand";
import { FIRST_GUIDE_STEP } from "../constants/studioTabs";
import {
  INITIAL_TABS_LAYOUT,
  OpenTabOptions,
  closeOtherTabsLayout,
  closeTabLayout,
  focusTabLayout,
  moveTabLayout,
  openTabLayout,
  pruneCardTabsLayout,
  sanitizeLayout,
  setSplitLayout,
} from "../lib/studioTabsState";
import { remapGuideStep } from "../lib/guideStepsFor";
import type { GuideView, PersistedStudioTabs } from "../types/studioTab.types";

interface StudioTabsState {
  openTabIds: string[];
  activeTabId: string | null;
  splitTabId: string | null;
  guideStep: number;
  isGuideStepAdvanced: boolean | null;
  guideView: GuideView;
  isChatOpen: boolean;
  isResumePending: boolean;
  welcomeBackStepName: string | null;
  openTab: (tabId: string, options?: OpenTabOptions) => void;
  closeTab: (tabId: string) => void;
  closeOtherTabs: (tabId: string) => void;
  focusTab: (tabId: string) => void;
  setSplit: (tabId: string | null) => void;
  moveTab: (fromIndex: number, toIndex: number) => void;
  pruneCardTabs: (existingEntityIds: Set<string>) => void;
  setGuideStep: (step: number) => void;
  setGuideStepMode: (isAdvanced: boolean) => void;
  reconcileGuideStep: (isAdvanced: boolean) => void;
  setGuideView: (view: GuideView) => void;
  setChatOpen: (isOpen: boolean) => void;
  markResumePending: () => void;
  completeResume: (stepNumber: number | null, stepName: string | null) => void;
  clearWelcomeBack: () => void;
  restoreTabs: (snapshot: PersistedStudioTabs) => void;
  resetTabs: () => void;
}

export const useStudioTabsStore = create<StudioTabsState>((set) => ({
  ...INITIAL_TABS_LAYOUT,
  guideStep: FIRST_GUIDE_STEP,
  isGuideStepAdvanced: null,
  guideView: "steps",
  isChatOpen: false,
  isResumePending: false,
  welcomeBackStepName: null,
  openTab: (tabId, options) => set((state) => openTabLayout(state, tabId, options)),
  closeTab: (tabId) => set((state) => closeTabLayout(state, tabId)),
  closeOtherTabs: (tabId) => set((state) => closeOtherTabsLayout(state, tabId)),
  focusTab: (tabId) => set((state) => focusTabLayout(state, tabId)),
  setSplit: (tabId) => set((state) => setSplitLayout(state, tabId)),
  moveTab: (fromIndex, toIndex) =>
    set((state) => moveTabLayout(state, fromIndex, toIndex)),
  pruneCardTabs: (existingEntityIds) =>
    set((state) => pruneCardTabsLayout(state, existingEntityIds)),
  setGuideStep: (step) => set({ guideStep: step, isResumePending: false }),
  setGuideStepMode: (isAdvanced) => set({ isGuideStepAdvanced: isAdvanced }),
  reconcileGuideStep: (isAdvanced) =>
    set((state) => {
      const wasAdvanced = state.isGuideStepAdvanced;
      if (wasAdvanced === null || wasAdvanced === isAdvanced) return { isGuideStepAdvanced: isAdvanced };
      return {
        guideStep: remapGuideStep(state.guideStep, wasAdvanced, isAdvanced),
        isGuideStepAdvanced: isAdvanced,
      };
    }),
  setGuideView: (view) => set({ guideView: view }),
  setChatOpen: (isOpen) => set({ isChatOpen: isOpen }),
  markResumePending: () => set({ isResumePending: true, welcomeBackStepName: null }),
  completeResume: (stepNumber, stepName) =>
    set((state) =>
      state.isResumePending
        ? {
            isResumePending: false,
            welcomeBackStepName: stepName,
            guideStep: stepNumber ?? state.guideStep,
          }
        : state,
    ),
  clearWelcomeBack: () => set({ welcomeBackStepName: null }),
  restoreTabs: (snapshot) =>
    set({
      ...sanitizeLayout(snapshot),
      guideStep: snapshot.guideStep,
      isGuideStepAdvanced: snapshot.isGuideStepAdvanced ?? null,
    }),
  resetTabs: () =>
    set({
      ...INITIAL_TABS_LAYOUT,
      guideStep: FIRST_GUIDE_STEP,
      isGuideStepAdvanced: null,
      guideView: "steps",
      isResumePending: false,
      welcomeBackStepName: null,
    }),
}));
