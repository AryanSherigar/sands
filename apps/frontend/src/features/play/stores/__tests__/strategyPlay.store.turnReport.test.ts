import { beforeEach, describe, expect, it } from "vitest";
import { useStrategyPlayStore } from "../strategyPlay.store";
import type { StrategyTurnReportData } from "../../types/turnReport.types";

const MOCK_REPORT: StrategyTurnReportData = {
  turn: 1,
  seasonTitle: "Summer, Year 3",
  headline: "Greywater Ford held",
  quickStats: {
    netGold: -22,
    totalCasualties: 184,
    stability: 78,
    stabilityDelta: -4,
    manpower: 3240,
  },
  battles: [],
  economyLines: [],
  items: [],
};

describe("useStrategyPlayStore - Turn Report", () => {
  beforeEach(() => {
    localStorage.clear();
    useStrategyPlayStore.getState().reset();
  });

  it("initializes with turn report closed and autoShow true", () => {
    const state = useStrategyPlayStore.getState();
    expect(state.isTurnReportOpen).toBe(false);
    expect(state.hasUnreadTurnReport).toBe(false);
    expect(state.autoShowTurnReport).toBe(true);
    expect(state.activeReportFilter).toBe("all");
    expect(state.latestReport).toBeNull();
  });

  it("opens turn report, cancels targeting, and clears selected entity", () => {
    useStrategyPlayStore.getState().selectEntity({ type: "region", id: "ashford" });
    useStrategyPlayStore.getState().startTargeting({ action: "move", sourceArmyId: "army-1" });
    expect(useStrategyPlayStore.getState().selectedEntity).not.toBeNull();
    expect(useStrategyPlayStore.getState().targeting).not.toBeNull();

    useStrategyPlayStore.getState().openTurnReport();
    const state = useStrategyPlayStore.getState();
    expect(state.isTurnReportOpen).toBe(true);
    expect(state.selectedEntity).toBeNull();
    expect(state.targeting).toBeNull();
    expect(state.hasUnreadTurnReport).toBe(false);
  });

  it("closes turn report when selecting an entity", () => {
    useStrategyPlayStore.getState().openTurnReport();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);

    useStrategyPlayStore.getState().selectEntity({ type: "region", id: "ashford" });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
    expect(useStrategyPlayStore.getState().selectedEntity?.id).toBe("ashford");
  });

  it("closes turn report via closeTurnReport", () => {
    useStrategyPlayStore.getState().openTurnReport();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);

    useStrategyPlayStore.getState().closeTurnReport();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("toggles turn report open and closed", () => {
    useStrategyPlayStore.getState().toggleTurnReport();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);

    useStrategyPlayStore.getState().toggleTurnReport();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("updates active filter and latest report", () => {
    useStrategyPlayStore.getState().setActiveReportFilter("military");
    useStrategyPlayStore.getState().setLatestReport(MOCK_REPORT);
    useStrategyPlayStore.getState().focusMapLocation("greywater");

    const state = useStrategyPlayStore.getState();
    expect(state.activeReportFilter).toBe("military");
    expect(state.latestReport?.headline).toBe("Greywater Ford held");
    expect(state.mapFocusTarget?.regionId).toBe("greywater");
  });

  it("persists autoShowTurnReport preference to localStorage", () => {
    useStrategyPlayStore.getState().setAutoShowTurnReport(false);
    expect(useStrategyPlayStore.getState().autoShowTurnReport).toBe(false);
    expect(localStorage.getItem("strategy_auto_show_turn_report")).toBe("false");

    useStrategyPlayStore.getState().setAutoShowTurnReport(true);
    expect(useStrategyPlayStore.getState().autoShowTurnReport).toBe(true);
    expect(localStorage.getItem("strategy_auto_show_turn_report")).toBe("true");
  });
});
