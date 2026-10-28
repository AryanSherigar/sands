import { create } from "zustand";
import type { StrategyPlayState } from "./strategyPlay.types";

const AUTO_SHOW_STORAGE_KEY = "strategy_auto_show_turn_report";

function getInitialAutoShow(): boolean {
  if (typeof window === "undefined" || !window.localStorage) {
    return true;
  }
  try {
    const item = window.localStorage.getItem(AUTO_SHOW_STORAGE_KEY);
    return item === null ? true : item === "true";
  } catch {
    return true;
  }
}

function saveAutoShow(autoShow: boolean): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    window.localStorage.setItem(AUTO_SHOW_STORAGE_KEY, String(autoShow));
  } catch {
    // Storage access error fallback
  }
}

const INITIAL_STATE = {
  selectedEntity: null,
  activeMapMode: "political" as const,
  targeting: null,
  activeRightTab: null,
  isRightDrawerPinned: false,
  orderFeedback: null,
  isTurnReportOpen: false,
  hasUnreadTurnReport: false,
  autoShowTurnReport: true,
  activeReportFilter: "all" as const,
  latestReport: null,
  mapFocusTarget: null,
  activeSceneId: null,
  isSituationsOpen: false,
  activeSituationId: null,
};

export const useStrategyPlayStore = create<StrategyPlayState>((set) => ({
  ...INITIAL_STATE,
  autoShowTurnReport: getInitialAutoShow(),
  selectEntity: (selectedEntity) =>
    set((state) => ({
      selectedEntity,
      targeting: null,
      isTurnReportOpen: selectedEntity !== null ? false : state.isTurnReportOpen,
    })),
  setActiveMapMode: (activeMapMode) => set({ activeMapMode }),
  startTargeting: (targeting) => set({ targeting }),
  cancelTargeting: () => set({ targeting: null }),
  setActiveRightTab: (activeRightTab) => set({ activeRightTab }),
  togglePinRightDrawer: () =>
    set((state) => ({ isRightDrawerPinned: !state.isRightDrawerPinned })),
  setOrderFeedback: (orderFeedback) => set({ orderFeedback }),
  openTurnReport: () =>
    set({
      isTurnReportOpen: true,
      selectedEntity: null,
      targeting: null,
      hasUnreadTurnReport: false,
    }),
  closeTurnReport: () => set({ isTurnReportOpen: false }),
  toggleTurnReport: () =>
    set((state) => {
      const isOpening = !state.isTurnReportOpen;
      return {
        isTurnReportOpen: isOpening,
        ...(isOpening ? { selectedEntity: null, hasUnreadTurnReport: false } : {}),
      };
    }),
  setAutoShowTurnReport: (autoShowTurnReport) => {
    saveAutoShow(autoShowTurnReport);
    set({ autoShowTurnReport });
  },
  setActiveReportFilter: (activeReportFilter) => set({ activeReportFilter }),
  setLatestReport: (latestReport) => set({ latestReport }),
  focusMapLocation: (regionId) =>
    set({ mapFocusTarget: { regionId, timestamp: Date.now() } }),
  openScene: (activeSceneId) => set({ activeSceneId }),
  closeScene: () => set({ activeSceneId: null }),
  openSituations: (situationId) =>
    set({ isSituationsOpen: true, activeSituationId: situationId ?? null }),
  closeSituations: () =>
    set({ isSituationsOpen: false, activeSituationId: null }),
  toggleSituations: () =>
    set((s) => ({ isSituationsOpen: !s.isSituationsOpen })),
  reset: () =>
    set({
      ...INITIAL_STATE,
      autoShowTurnReport: getInitialAutoShow(),
    }),
}));
