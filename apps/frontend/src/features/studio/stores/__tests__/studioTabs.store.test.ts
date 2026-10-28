import { beforeEach, describe, expect, it } from "vitest";
import { GUIDE_TAB_ID, PLAYTEST_TAB_ID } from "../../constants/studioTabs";
import { buildCardTabId, parseTabId } from "../../lib/studioTabs";
import { useStudioTabsStore } from "../studioTabs.store";

const mara = buildCardTabId("mara");
const lighthouse = buildCardTabId("lighthouse");
const tomas = buildCardTabId("tomas");

const getState = () => useStudioTabsStore.getState();

describe("studioTabs store", () => {
  beforeEach(() => {
    getState().resetTabs();
  });

  it("starts with only the Guide tab on step 1", () => {
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID]);
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
    expect(getState().splitTabId).toBeNull();
    expect(getState().guideStep).toBe(1);
  });

  it("opens a new tab and focuses it", () => {
    getState().openTab(mara);
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID, mara]);
    expect(getState().activeTabId).toBe(mara);
  });

  it("focuses an already open item instead of opening a second tab", () => {
    getState().openTab(mara);
    getState().openTab(lighthouse);
    getState().openTab(mara);
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID, mara, lighthouse]);
    expect(getState().activeTabId).toBe(mara);
  });

  it("opens a tab in the split pane when asked", () => {
    getState().openTab(PLAYTEST_TAB_ID, { isSplit: true });
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
    expect(getState().splitTabId).toBe(PLAYTEST_TAB_ID);
  });

  it("splits an open tab to the right and keeps the active tab", () => {
    getState().openTab(mara);
    getState().openTab(lighthouse);
    getState().setSplit(mara);
    expect(getState().activeTabId).toBe(lighthouse);
    expect(getState().splitTabId).toBe(mara);
  });

  it("splitting the active tab hands focus to a neighbour", () => {
    getState().openTab(mara);
    getState().setSplit(mara);
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
    expect(getState().splitTabId).toBe(mara);
  });

  it("refuses to split the only open tab", () => {
    getState().setSplit(GUIDE_TAB_ID);
    expect(getState().splitTabId).toBeNull();
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
  });

  it("swaps panes when the split tab is focused", () => {
    getState().openTab(mara);
    getState().setSplit(GUIDE_TAB_ID);
    getState().focusTab(GUIDE_TAB_ID);
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
    expect(getState().splitTabId).toBe(mara);
  });

  it("closing the active tab focuses its right neighbour, else the left", () => {
    getState().openTab(mara);
    getState().openTab(lighthouse);
    getState().focusTab(mara);
    getState().closeTab(mara);
    expect(getState().activeTabId).toBe(lighthouse);
    getState().closeTab(lighthouse);
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
  });

  it("closing the split tab clears the split", () => {
    getState().openTab(mara);
    getState().setSplit(mara);
    getState().closeTab(mara);
    expect(getState().splitTabId).toBeNull();
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID]);
  });

  it("allows closing every tab, including the Guide", () => {
    getState().closeTab(GUIDE_TAB_ID);
    expect(getState().openTabIds).toEqual([]);
    expect(getState().activeTabId).toBeNull();
    getState().openTab(GUIDE_TAB_ID);
    expect(getState().activeTabId).toBe(GUIDE_TAB_ID);
  });

  it("closes every other tab", () => {
    getState().openTab(mara);
    getState().openTab(lighthouse);
    getState().closeOtherTabs(mara);
    expect(getState().openTabIds).toEqual([mara]);
    expect(getState().activeTabId).toBe(mara);
    expect(getState().splitTabId).toBeNull();
  });

  it("reorders tabs", () => {
    getState().openTab(mara);
    getState().openTab(lighthouse);
    getState().moveTab(2, 0);
    expect(getState().openTabIds).toEqual([lighthouse, GUIDE_TAB_ID, mara]);
  });

  it("prunes card tabs whose card no longer exists", () => {
    getState().openTab(mara);
    getState().openTab(tomas);
    getState().pruneCardTabs(new Set(["tomas"]));
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID, tomas]);
    expect(getState().activeTabId).toBe(tomas);
  });

  it("restores a snapshot and drops unknown tab ids", () => {
    getState().restoreTabs({
      openTabIds: [GUIDE_TAB_ID, mara, "nonsense"],
      activeTabId: mara,
      splitTabId: "nonsense",
      guideStep: 4,
    });
    expect(getState().openTabIds).toEqual([GUIDE_TAB_ID, mara]);
    expect(getState().activeTabId).toBe(mara);
    expect(getState().splitTabId).toBeNull();
    expect(getState().guideStep).toBe(4);
  });

  it("parses every tab kind", () => {
    expect(parseTabId(GUIDE_TAB_ID)?.kind).toBe("guide");
    expect(parseTabId(mara)).toEqual({ kind: "card", targetId: "mara" });
    expect(parseTabId(PLAYTEST_TAB_ID)?.kind).toBe("playtest");
    expect(parseTabId("feature:triggers")).toEqual({
      kind: "feature",
      targetId: "triggers",
    });
    expect(parseTabId("nonsense")).toBeNull();
  });

  describe("reconcileGuideStep", () => {
    const ENDINGS_STEP = 7;
    const BASE_FINISH_STEP = 7;
    const ADVANCED_FINISH_STEP = 12;
    const OPENING_STEP = 6;

    it("only learns which mode the saved step belongs to when it had none", () => {
      getState().setGuideStep(ENDINGS_STEP);
      getState().reconcileGuideStep(true);
      expect(getState().guideStep).toBe(ENDINGS_STEP);
      expect(getState().isGuideStepAdvanced).toBe(true);
    });

    it("moves Finish to its Advanced number when the story went Advanced elsewhere", () => {
      getState().setGuideStep(BASE_FINISH_STEP);
      getState().setGuideStepMode(false);
      getState().reconcileGuideStep(true);
      expect(getState().guideStep).toBe(ADVANCED_FINISH_STEP);
      expect(getState().isGuideStepAdvanced).toBe(true);
    });

    it("falls back to Opening when the saved Advanced step no longer exists", () => {
      getState().setGuideStep(ENDINGS_STEP);
      getState().setGuideStepMode(true);
      getState().reconcileGuideStep(false);
      expect(getState().guideStep).toBe(OPENING_STEP);
    });

    it("leaves the step alone when the mode did not change", () => {
      getState().setGuideStep(ENDINGS_STEP);
      getState().setGuideStepMode(true);
      getState().reconcileGuideStep(true);
      expect(getState().guideStep).toBe(ENDINGS_STEP);
    });
  });
});
