import { moveItem } from "@/shared/lib/moveItem";
import { GUIDE_TAB_ID } from "../constants/studioTabs";
import { isCardTabId, parseTabId } from "./studioTabs";

export interface TabsLayout {
  openTabIds: string[];
  activeTabId: string | null;
  splitTabId: string | null;
}

export interface OpenTabOptions {
  isSplit?: boolean;
}

export const INITIAL_TABS_LAYOUT: TabsLayout = {
  openTabIds: [GUIDE_TAB_ID],
  activeTabId: GUIDE_TAB_ID,
  splitTabId: null,
};

const pickNeighbour = (tabIds: string[], index: number): string | null =>
  tabIds[index] ?? tabIds[index - 1] ?? null;

export const focusTabLayout = (layout: TabsLayout, tabId: string): TabsLayout => {
  if (!layout.openTabIds.includes(tabId)) return layout;
  if (tabId === layout.splitTabId) {
    return { ...layout, activeTabId: tabId, splitTabId: layout.activeTabId };
  }
  return { ...layout, activeTabId: tabId };
};

export const openTabLayout = (
  layout: TabsLayout,
  tabId: string,
  options: OpenTabOptions = {},
): TabsLayout => {
  if (!parseTabId(tabId)) return layout;
  const isAlreadyOpen = layout.openTabIds.includes(tabId);
  const openTabIds = isAlreadyOpen ? layout.openTabIds : [...layout.openTabIds, tabId];
  const withTab = { ...layout, openTabIds };
  if (options.isSplit && tabId !== layout.activeTabId && layout.activeTabId) {
    return { ...withTab, splitTabId: tabId };
  }
  return focusTabLayout(withTab, tabId);
};

export const closeTabLayout = (layout: TabsLayout, tabId: string): TabsLayout => {
  const index = layout.openTabIds.indexOf(tabId);
  if (index === -1) return layout;
  const openTabIds = layout.openTabIds.filter((id) => id !== tabId);
  const splitTabId = layout.splitTabId === tabId ? null : layout.splitTabId;
  if (layout.activeTabId !== tabId) return { ...layout, openTabIds, splitTabId };
  const activeTabId = pickNeighbour(
    openTabIds.filter((id) => id !== splitTabId),
    index,
  );
  return { openTabIds, activeTabId, splitTabId };
};

export const closeOtherTabsLayout = (layout: TabsLayout, tabId: string): TabsLayout =>
  layout.openTabIds.includes(tabId)
    ? { openTabIds: [tabId], activeTabId: tabId, splitTabId: null }
    : layout;

export const setSplitLayout = (layout: TabsLayout, tabId: string | null): TabsLayout => {
  if (tabId === null) return { ...layout, splitTabId: null };
  if (!layout.openTabIds.includes(tabId)) return layout;
  if (tabId !== layout.activeTabId) return { ...layout, splitTabId: tabId };
  const others = layout.openTabIds.filter((id) => id !== tabId);
  if (others.length === 0) return layout;
  return { ...layout, activeTabId: others[0], splitTabId: tabId };
};

export const moveTabLayout = (
  layout: TabsLayout,
  fromIndex: number,
  toIndex: number,
): TabsLayout => ({
  ...layout,
  openTabIds: moveItem(layout.openTabIds, fromIndex, toIndex),
});

export const pruneCardTabsLayout = (
  layout: TabsLayout,
  existingEntityIds: Set<string>,
): TabsLayout => {
  const isKept = (tabId: string): boolean =>
    !isCardTabId(tabId) || existingEntityIds.has(parseTabId(tabId)?.targetId ?? "");
  const openTabIds = layout.openTabIds.filter(isKept);
  if (openTabIds.length === layout.openTabIds.length) return layout;
  const closedIds = layout.openTabIds.filter((id) => !isKept(id));
  return closedIds.reduce(closeTabLayout, layout);
};

export const sanitizeLayout = (layout: TabsLayout): TabsLayout => {
  const openTabIds = layout.openTabIds.filter((id) => parseTabId(id) !== null);
  const isOpen = (id: string | null): id is string => id !== null && openTabIds.includes(id);
  const activeTabId = isOpen(layout.activeTabId) ? layout.activeTabId : openTabIds[0] ?? null;
  const splitTabId =
    isOpen(layout.splitTabId) && layout.splitTabId !== activeTabId ? layout.splitTabId : null;
  return { openTabIds, activeTabId, splitTabId };
};
