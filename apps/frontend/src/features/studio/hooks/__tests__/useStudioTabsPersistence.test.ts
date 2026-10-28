import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  GUIDE_TAB_ID,
  STUDIO_TABS_STORAGE_PREFIX,
} from "../../constants/studioTabs";
import { buildCardTabId } from "../../lib/studioTabs";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { useStudioTabsPersistence } from "../useStudioTabsPersistence";

const STORY_ID = "story-1";
const STORAGE_KEY = `${STUDIO_TABS_STORAGE_PREFIX}${STORY_ID}`;
const mara = buildCardTabId("mara");

describe("useStudioTabsPersistence", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("restores the tabs remembered for this story on this device", () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        openTabIds: [GUIDE_TAB_ID, mara],
        activeTabId: mara,
        splitTabId: null,
        guideStep: 3,
      }),
    );
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    const state = useStudioTabsStore.getState();
    expect(state.openTabIds).toEqual([GUIDE_TAB_ID, mara]);
    expect(state.activeTabId).toBe(mara);
    expect(state.guideStep).toBe(3);
  });

  it("restores which mode the saved Guide step belongs to", () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        openTabIds: [GUIDE_TAB_ID],
        activeTabId: GUIDE_TAB_ID,
        splitTabId: null,
        guideStep: 7,
        isGuideStepAdvanced: true,
      }),
    );
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    expect(useStudioTabsStore.getState().isGuideStepAdvanced).toBe(true);
  });

  it("remembers the mode of the Guide step with the step", () => {
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    useStudioTabsStore.getState().setGuideStepMode(true);
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(saved.isGuideStepAdvanced).toBe(true);
  });

  it("remembers tab changes per story", () => {
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    useStudioTabsStore.getState().openTab(mara);
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(saved.openTabIds).toEqual([GUIDE_TAB_ID, mara]);
    expect(saved.activeTabId).toBe(mara);
  });

  it("opens only the Guide when the saved value is corrupt", () => {
    localStorage.setItem(STORAGE_KEY, "{not json");
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    expect(useStudioTabsStore.getState().openTabIds).toEqual([GUIDE_TAB_ID]);
  });

  it("opens only the Guide when localStorage is unavailable", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    renderHook(() => useStudioTabsPersistence(STORY_ID));
    useStudioTabsStore.getState().openTab(mara);
    expect(useStudioTabsStore.getState().openTabIds).toEqual([GUIDE_TAB_ID, mara]);
  });

  it("does not remember anything before the story exists", () => {
    renderHook(() => useStudioTabsPersistence(null));
    useStudioTabsStore.getState().openTab(mara);
    expect(localStorage.length).toBe(0);
  });

  it("keeps the open tabs when the draft story is created", () => {
    const { rerender } = renderHook(
      ({ id }: { id: string | null }) => useStudioTabsPersistence(id),
      { initialProps: { id: null as string | null } },
    );
    useStudioTabsStore.getState().setGuideStep(2);
    rerender({ id: STORY_ID });
    expect(useStudioTabsStore.getState().guideStep).toBe(2);
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(saved.guideStep).toBe(2);
  });
});
