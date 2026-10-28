import { describe, it, expect, beforeEach } from "vitest";
import { useStrategyPlayStore } from "../strategyPlay.store";

describe("useStrategyPlayStore", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().reset();
  });

  it("selects and deselects an entity", () => {
    expect(useStrategyPlayStore.getState().selectedEntity).toBeNull();
    useStrategyPlayStore.getState().selectEntity({ type: "region", id: "region-1" });
    expect(useStrategyPlayStore.getState().selectedEntity).toEqual({ type: "region", id: "region-1" });
    useStrategyPlayStore.getState().selectEntity(null);
    expect(useStrategyPlayStore.getState().selectedEntity).toBeNull();
  });

  it("changes active map mode", () => {
    expect(useStrategyPlayStore.getState().activeMapMode).toBe("political");
    useStrategyPlayStore.getState().setActiveMapMode("terrain");
    expect(useStrategyPlayStore.getState().activeMapMode).toBe("terrain");
  });

  it("manages targeting state and cancels it", () => {
    useStrategyPlayStore.getState().startTargeting({ action: "move", sourceArmyId: "army-1" });
    expect(useStrategyPlayStore.getState().targeting).toEqual({ action: "move", sourceArmyId: "army-1" });
    useStrategyPlayStore.getState().cancelTargeting();
    expect(useStrategyPlayStore.getState().targeting).toBeNull();
  });

  it("toggles right drawer pinning", () => {
    expect(useStrategyPlayStore.getState().isRightDrawerPinned).toBe(false);
    useStrategyPlayStore.getState().togglePinRightDrawer();
    expect(useStrategyPlayStore.getState().isRightDrawerPinned).toBe(true);
  });

  it("switches active right tab", () => {
    expect(useStrategyPlayStore.getState().activeRightTab).toBeNull();
    useStrategyPlayStore.getState().setActiveRightTab("factions");
    expect(useStrategyPlayStore.getState().activeRightTab).toBe("factions");
  });

  it("clears targeting when selecting an entity", () => {
    useStrategyPlayStore.getState().startTargeting({ action: "move", sourceArmyId: "army-1" });
    useStrategyPlayStore.getState().selectEntity({ type: "region", id: "region-2" });
    expect(useStrategyPlayStore.getState().targeting).toBeNull();
    expect(useStrategyPlayStore.getState().selectedEntity).toEqual({ type: "region", id: "region-2" });
  });

  it("manages situations drawer state", () => {
    const store = useStrategyPlayStore.getState();
    expect(store.isSituationsOpen).toBe(false);

    store.openSituations("situation-ashford");
    expect(useStrategyPlayStore.getState().isSituationsOpen).toBe(true);
    expect(useStrategyPlayStore.getState().activeSituationId).toBe("situation-ashford");

    store.closeSituations();
    expect(useStrategyPlayStore.getState().isSituationsOpen).toBe(false);
    expect(useStrategyPlayStore.getState().activeSituationId).toBeNull();
  });
});
