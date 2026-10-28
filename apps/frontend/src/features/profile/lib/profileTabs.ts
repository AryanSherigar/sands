import {
  PROFILE_TABS,
  type ProfileTabDefinition,
  type ProfileTabId,
} from "../constants/profileTabs.constants";

export const getVisibleTabs = (isOwnerView: boolean): ProfileTabDefinition[] =>
  PROFILE_TABS.filter((tab) => isOwnerView || !tab.isOwnerOnly);

export const resolveProfileTab = (
  param: string | null,
  visibleTabs: ProfileTabDefinition[],
): ProfileTabId => {
  const match = visibleTabs.find((tab) => tab.id === param);
  return match ? match.id : visibleTabs[0].id;
};

export const getNextTabIndex = (
  currentIndex: number,
  tabCount: number,
  key: string,
): number | null => {
  if (key === "ArrowRight") return (currentIndex + 1) % tabCount;
  if (key === "ArrowLeft") return (currentIndex - 1 + tabCount) % tabCount;
  if (key === "Home") return 0;
  if (key === "End") return tabCount - 1;
  return null;
};

export const getProfileTabId = (id: ProfileTabId): string =>
  `profile-tab-${id}`;

export const getProfilePanelId = (id: ProfileTabId): string =>
  `profile-panel-${id}`;

export const isOwnerOnlyTab = (param: string | null): boolean =>
  PROFILE_TABS.some((tab) => tab.id === param && tab.isOwnerOnly);
