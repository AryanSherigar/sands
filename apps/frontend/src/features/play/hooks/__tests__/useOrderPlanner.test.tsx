import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useOrderPlanner } from "../useOrderPlanner";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";

const mockCheck = vi.fn();
const mockMutateAsync = vi.fn();

vi.mock("../useSimulationCommands", () => ({
  useSimulationCommands: () => ({
    acceptMutation: { mutateAsync: mockMutateAsync },
    cancelMutation: { mutate: vi.fn() },
    check: mockCheck,
  }),
}));

const FACTION_ID = DEFAULT_PREVIEW_WORLD.my_faction.id;

describe("useOrderPlanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStrategyPlayStore.getState().reset();
  });

  it("accepts an order that passes the dry run", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => result.current.handleInspectorAction({ type: "halt", armyId: "army-royal-1" }));
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "halt_army",
      faction_id: FACTION_ID,
      army_id: "army-royal-1",
    });
  });

  it("shows the refusal reason and does not accept a flagged order", async () => {
    mockCheck.mockResolvedValue({ flag: "over_budget", reason: "Not enough mandates", orders_remaining: 0 });
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => result.current.handleInspectorAction({ type: "levy", regionId: "reg-dunmere" }));
    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toBe("Not enough mandates");
  });

  it("turns a move action plus a region click into a move order", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result, rerender } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    act(() => result.current.handleInspectorAction({ type: "move", armyId: "army-royal-1" }));
    rerender();
    expect(result.current.targeting).toEqual({ action: "move", sourceArmyId: "army-royal-1" });
    await act(async () => result.current.handleRegionTargeted("reg-greenford"));
    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "move_army", to_region_id: "reg-greenford" }),
    );
    expect(useStrategyPlayStore.getState().targeting).toBeNull();
  });

  it("explains that orders are disabled without a playthrough", async () => {
    const { result } = renderHook(() => useOrderPlanner(undefined, DEFAULT_PREVIEW_WORLD));
    await act(async () => result.current.handleInspectorAction({ type: "halt", armyId: "army-royal-1" }));
    expect(mockCheck).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toMatch(/preview/i);
  });
});
