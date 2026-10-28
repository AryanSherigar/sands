import type {
  StrategyTurnReportData,
  TurnReportCategory,
} from "../types/turnReport.types";

export type StrategyMapMode = "political" | "terrain" | "diplomacy" | "fog";

export type StrategyTargetingAction = "move" | "attack";

export interface StrategyTargetingState {
  action: StrategyTargetingAction;
  sourceArmyId: string;
}

export interface StrategyOrderFeedback {
  message: string;
}

export type SelectedEntity =
  | { type: "region"; id: string }
  | { type: "army"; id: string };

export interface MapFocusTarget {
  regionId: string;
  timestamp: number;
}

export interface StrategyPlayState {
  selectedEntity: SelectedEntity | null;
  activeMapMode: StrategyMapMode;
  targeting: StrategyTargetingState | null;
  activeRightTab: "factions" | "chronicle" | null;
  isRightDrawerPinned: boolean;
  orderFeedback: StrategyOrderFeedback | null;
  isTurnReportOpen: boolean;
  hasUnreadTurnReport: boolean;
  autoShowTurnReport: boolean;
  activeReportFilter: TurnReportCategory;
  latestReport: StrategyTurnReportData | null;
  mapFocusTarget: MapFocusTarget | null;
  activeSceneId: string | null;
  isSituationsOpen: boolean;
  activeSituationId: string | null;
  selectEntity: (entity: SelectedEntity | null) => void;
  setActiveMapMode: (mode: StrategyMapMode) => void;
  startTargeting: (targeting: StrategyTargetingState) => void;
  cancelTargeting: () => void;
  setActiveRightTab: (tab: "factions" | "chronicle" | null) => void;
  togglePinRightDrawer: () => void;
  setOrderFeedback: (feedback: StrategyOrderFeedback | null) => void;
  openTurnReport: () => void;
  closeTurnReport: () => void;
  toggleTurnReport: () => void;
  setAutoShowTurnReport: (autoShow: boolean) => void;
  setActiveReportFilter: (filter: TurnReportCategory) => void;
  setLatestReport: (report: StrategyTurnReportData | null) => void;
  focusMapLocation: (regionId: string) => void;
  openScene: (sceneId: string) => void;
  closeScene: () => void;
  openSituations: (situationId?: string) => void;
  closeSituations: () => void;
  toggleSituations: () => void;
  reset: () => void;
}
