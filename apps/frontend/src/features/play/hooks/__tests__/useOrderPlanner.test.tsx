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

  it("refuses to issue any order once the reign has ended", async () => {
    const endedWorld = {
      ...DEFAULT_PREVIEW_WORLD,
      ending: { ending_id: "default_defeat_capital_lost", kind: "defeat" as const, turn: 2 },
    };
    const { result } = renderHook(() => useOrderPlanner("pt-1", endedWorld));
    await act(async () => result.current.handleInspectorAction({ type: "halt", armyId: "army-royal-1" }));
    expect(mockCheck).not.toHaveBeenCalled();
    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toBe("The reign has ended.");
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

  it("submits declare war order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "declare_war", targetFactionId: "faction-mira" });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "declare_war",
      faction_id: FACTION_ID,
      target_faction_id: "faction-mira",
      ground_id: null,
    });
  });

  it("submits sue peace order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "sue_peace", warId: "war-10" });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "sue_peace",
      faction_id: FACTION_ID,
      war_id: "war-10",
    });
  });

  it("submits send envoy order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "send_envoy", targetFactionId: "faction-mira" });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "send_envoy",
      faction_id: FACTION_ID,
      target_faction_id: "faction-mira",
    });
  });

  it("submits call negotiation order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "call_negotiation", targetFactionId: "faction-mira" });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "call_negotiation",
      faction_id: FACTION_ID,
      target_faction_id: "faction-mira",
    });
  });

  it("submits answer call order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "answer_call", callId: "c-1", isJoining: true });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "answer_call",
      faction_id: FACTION_ID,
      call_id: "c-1",
      is_joining: true,
    });
  });

  it("submits answer demand order via inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => {
      result.current.handleInspectorAction({ type: "answer_demand", demandId: "d-1", reply: "accept" });
    });
    expect(mockMutateAsync).toHaveBeenCalledWith({
      kind: "answer_demand",
      faction_id: FACTION_ID,
      demand_id: "d-1",
      reply: "accept",
    });
  });

  it("moves a whole group with one order per army", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const store = useStrategyPlayStore.getState();
    store.toggleGroupArmy("army-a");
    store.toggleGroupArmy("army-b");
    const { result, rerender } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    act(() => result.current.handleGroupAction("move"));
    rerender();
    await act(async () => result.current.handleRegionTargeted("reg-greenford"));

    expect(mockMutateAsync).toHaveBeenCalledTimes(2);
    expect(mockMutateAsync).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ kind: "move_army", army_id: "army-a", to_region_id: "reg-greenford" }),
    );
    expect(mockMutateAsync).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ kind: "move_army", army_id: "army-b" }),
    );
    expect(useStrategyPlayStore.getState().groupArmyIds).toEqual([]);
  });

  it("halts a whole group and clears it", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const store = useStrategyPlayStore.getState();
    store.toggleGroupArmy("army-a");
    store.toggleGroupArmy("army-b");
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () => result.current.handleGroupAction("halt"));

    expect(mockMutateAsync).toHaveBeenCalledTimes(2);
    expect(useStrategyPlayStore.getState().groupArmyIds).toEqual([]);
  });

  it("merges the grouped armies into the first one", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const store = useStrategyPlayStore.getState();
    store.toggleGroupArmy("army-a");
    store.toggleGroupArmy("army-b");
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () => result.current.handleGroupAction("merge"));

    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "merge_armies", army_ids: ["army-a", "army-b"], into_army_id: "army-a" }),
    );
    expect(useStrategyPlayStore.getState().groupArmyIds).toEqual([]);
  });

  it("submits a split from the inspector action", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () => result.current.handleInspectorAction({ type: "split", armyId: "army-a", troops: { cavalry: 30 } }));

    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "split_army", army_id: "army-a", troops: { cavalry: 30 } }),
    );
  });

  it("submits an army preset from the inspector", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () =>
      result.current.handleInspectorAction({
        type: "set_army_policy",
        armyId: "army-a",
        policy: { reserve_policy: "reinforce_on_pressure" },
      }),
    );

    expect(mockMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "set_army_policy", army_id: "army-a", reserve_policy: "reinforce_on_pressure" }),
    );
  });

  it("refuses every order once the campaign has ended", async () => {
    const endedWorld = {
      ...DEFAULT_PREVIEW_WORLD,
      ending: { ending_id: "default_victory_conquest", kind: "victory", turn: 9 },
    };
    const { result } = renderHook(() => useOrderPlanner("pt-1", endedWorld));

    await act(async () => result.current.handleInspectorAction({ type: "halt", armyId: "army-royal-1" }));

    expect(mockCheck).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toBe("The reign has ended.");
  });

  it("issues scout, claim and disband orders from inspector actions", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () => result.current.handleInspectorAction({ type: "map_scout", regionId: "reg-x" }));
    await act(async () => result.current.handleInspectorAction({ type: "fabricate_claim", targetFactionId: "ash", regionId: "reg-x" }));
    await act(async () => result.current.handleInspectorAction({ type: "disband", armyId: "army-royal-1" }));

    expect(mockMutateAsync).toHaveBeenNthCalledWith(1, { kind: "map_scout", faction_id: FACTION_ID, target_region_id: "reg-x" });
    expect(mockMutateAsync).toHaveBeenNthCalledWith(2, { kind: "fabricate_claim", faction_id: FACTION_ID, target_faction_id: "ash", region_id: "reg-x" });
    expect(mockMutateAsync).toHaveBeenNthCalledWith(3, { kind: "disband_army", faction_id: FACTION_ID, army_id: "army-royal-1" });
  });

  it("refuses orders while a past turn is on screen", async () => {
    useStrategyPlayStore.getState().setHistoryTurn(2);
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));

    await act(async () => result.current.handleInspectorAction({ type: "halt", armyId: "army-royal-1" }));

    expect(mockCheck).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toContain("past turn");
  });

  it("declares war straight away when no cause is usable, and asks for a cause when one is", async () => {
    mockCheck.mockResolvedValue({ orders_remaining: 3 });
    mockMutateAsync.mockResolvedValue({});
    const { result } = renderHook(() => useOrderPlanner("pt-1", DEFAULT_PREVIEW_WORLD));
    await act(async () => result.current.handleInspectorAction({ type: "declare_war", targetFactionId: "ash" }));
    expect(mockMutateAsync).toHaveBeenCalledWith(expect.objectContaining({ kind: "declare_war", target_faction_id: "ash" }));

    mockMutateAsync.mockClear();
    const withGround = { ...DEFAULT_PREVIEW_WORLD, usable_grounds: [{ id: "g1", kind: "claim" as const, target_faction_id: "ash", region_id: "r1" }] };
    const second = renderHook(() => useOrderPlanner("pt-1", withGround));
    await act(async () => second.result.current.handleInspectorAction({ type: "declare_war", targetFactionId: "ash" }));

    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().pendingWarTargetId).toBe("ash");
  });
});
