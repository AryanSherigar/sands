type StudioTabKind = "guide" | "card" | "playtest" | "feature";

export type GuideView = "steps" | "editor";

export interface StudioTabTarget {
  kind: StudioTabKind;
  targetId: string | null;
}

export interface PersistedStudioTabs {
  openTabIds: string[];
  activeTabId: string | null;
  splitTabId: string | null;
  guideStep: number;
  isGuideStepAdvanced?: boolean | null;
}
