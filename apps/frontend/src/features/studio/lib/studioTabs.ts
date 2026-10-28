import {
  CARD_TAB_PREFIX,
  FEATURE_TAB_PREFIX,
  GUIDE_TAB_ID,
  PLAYTEST_TAB_ID,
} from "../constants/studioTabs";
import type { StudioTabTarget } from "../types/studioTab.types";

export const buildCardTabId = (entityId: string): string =>
  `${CARD_TAB_PREFIX}${entityId}`;

export const buildFeatureTabId = (featureId: string): string =>
  `${FEATURE_TAB_PREFIX}${featureId}`;

export const parseTabId = (tabId: string): StudioTabTarget | null => {
  if (tabId === GUIDE_TAB_ID) return { kind: "guide", targetId: null };
  if (tabId === PLAYTEST_TAB_ID) return { kind: "playtest", targetId: null };
  if (tabId.startsWith(CARD_TAB_PREFIX)) {
    return { kind: "card", targetId: tabId.slice(CARD_TAB_PREFIX.length) };
  }
  if (tabId.startsWith(FEATURE_TAB_PREFIX)) {
    return { kind: "feature", targetId: tabId.slice(FEATURE_TAB_PREFIX.length) };
  }
  return null;
};

export const isCardTabId = (tabId: string): boolean =>
  parseTabId(tabId)?.kind === "card";
