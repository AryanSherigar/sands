import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useStrategySetupState } from "../useStrategySetupState";
import { apiClient } from "@/shared/lib/api-client";

vi.mock("@/shared/lib/api-client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const mockScenario = {
  scenario_id: "scen-strat-1",
  strategy_document: {
    factions: [
      {
        id: "faction-a",
        name: "Realm of Valen",
        color: "#46606E",
        is_playable: true,
        leader_id: "leader-a",
        treasury: 500,
        manpower: 12000,
      },
      {
        id: "faction-b",
        name: "Marches of Oak",
        color: "#5E8A5A",
        is_playable: true,
        leader_id: "leader-b",
        treasury: 300,
        manpower: 7000,
      },
    ],
    leaders: [
      {
        id: "leader-a",
        name: "King Valen",
        epithet: "The Stalwart",
        portrait_url: "https://example.com/valen.png",
        trait_ids: ["cautious", "honorable"],
        ambition_ids: ["ambition_peace"],
        history: "A wise defender.",
      },
      {
        id: "leader-b",
        name: "Duchess Oak",
        epithet: "The Keen",
        portrait_url: "https://example.com/oak.png",
        trait_ids: ["pragmatic", "cautious"],
        ambition_ids: ["ambition_peace"],
        history: "A shrewd diplomat.",
      },
    ],
    ambitions: [
      { id: "ambition_peace", name: "Peace", description: "Maintain peace" },
    ],
  },
};

describe("useStrategySetupState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with first playable faction leader", () => {
    const { result } = renderHook(() => useStrategySetupState(mockScenario));
    expect(result.current.activeFactionId).toBe("faction-a");
    expect(result.current.ruler.name).toBe("King Valen");
    expect(result.current.ruler.epithet).toBe("The Stalwart");
    expect(result.current.ruler.traitIds).toEqual(["cautious", "honorable"]);
    expect(result.current.isValid).toBe(true);
  });

  it("switches faction and re-initializes ruler defaults", () => {
    const { result } = renderHook(() => useStrategySetupState(mockScenario));

    act(() => {
      result.current.setActiveFactionId("faction-b");
    });

    expect(result.current.activeFactionId).toBe("faction-b");
    expect(result.current.ruler.name).toBe("Duchess Oak");
    expect(result.current.ruler.epithet).toBe("The Keen");
  });

  it("updates ruler attributes and restores default ruler", () => {
    const { result } = renderHook(() => useStrategySetupState(mockScenario));

    act(() => {
      result.current.updateRuler({ name: "Custom Sovereign" });
    });
    expect(result.current.ruler.name).toBe("Custom Sovereign");

    act(() => {
      result.current.restoreDefaultRuler();
    });
    expect(result.current.ruler.name).toBe("King Valen");
  });

  it("validates ruler name and trait bounds", () => {
    const { result } = renderHook(() => useStrategySetupState(mockScenario));

    act(() => {
      result.current.updateRuler({ name: "" });
    });
    expect(result.current.isValid).toBe(false);
    expect(result.current.validation.name).toBeDefined();

    act(() => {
      result.current.updateRuler({ name: "Valid King", traitIds: ["honorable"] }); // 1 trait (min 2)
    });
    expect(result.current.isValid).toBe(false);
    expect(result.current.validation.traits).toBeDefined();
  });

  it("redrafts backstory via API", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { backstory: "Coronated amidst roaring thunder." },
    });

    const { result } = renderHook(() => useStrategySetupState(mockScenario));

    await act(async () => {
      await result.current.redraftBackstory();
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/strategy/ruler-backstory",
      expect.objectContaining({
        scenario_id: "scen-strat-1",
        faction_id: "faction-a",
        ruler_name: "King Valen",
      }),
    );
    expect(result.current.ruler.backstory).toBe("Coronated amidst roaring thunder.");
  });
});
