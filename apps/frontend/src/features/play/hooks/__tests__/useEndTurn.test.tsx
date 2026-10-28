import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useEndTurn } from "../useEndTurn";
import * as simulationApi from "../../api/simulation.api";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import type { CampaignWorldView, MutationResponse } from "../../types/simulation.types";

vi.mock("../../api/simulation.api");

const PLAYTHROUGH_ID = "pt-1";

const mutation = (status: MutationResponse["status"], worldVersion: number): MutationResponse => ({
  playthrough_id: PLAYTHROUGH_ID,
  world_version: worldVersion,
  world_hash: "hash",
  turn: 1,
  wave: 0,
  orders_remaining: 0,
  status,
  battles: [],
  operation_id: "op",
});

function renderEndTurn(world: Partial<CampaignWorldView> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  queryClient.setQueryData(["simulation-world", PLAYTHROUGH_ID], {
    world_version: 1,
    turn: 1,
    wave: 0,
    ...world,
  } as CampaignWorldView);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return renderHook(() => useEndTurn(PLAYTHROUGH_ID), { wrapper });
}

describe("useEndTurn", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStrategyPlayStore.getState().reset();
  });

  it("finishes immediately when the turn completes", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("turn_completed", 2));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("turn_completed"));
    expect(simulationApi.advanceBattles).not.toHaveBeenCalled();
  });

  it("leaves a battle decision pending without advancing or making a turn report", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("awaiting_battle_decision", 2));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("awaiting_battle_decision"));
    expect(simulationApi.advanceBattles).not.toHaveBeenCalled();
    expect(simulationApi.getTurnReport).not.toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().latestReport).toBeNull();
  });

  it("resumes exactly one player-controlled wave after reload", async () => {
    const battle = { id: "battle_1", region_id: "field", status: "awaiting_commands", exchanges_used: 0, total_exchanges: 0, control_mode: "player" as const };
    vi.mocked(simulationApi.advanceBattles).mockResolvedValue({ ...mutation("awaiting_commands", 3), battles: [battle], wave: 1 });
    const { result } = renderEndTurn({ status: "awaiting_commands", battles: [battle] });
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.world_version).toBe(3));
    expect(simulationApi.endTurn).not.toHaveBeenCalled();
    expect(simulationApi.advanceBattles).toHaveBeenCalledTimes(1);
    expect(vi.mocked(simulationApi.advanceBattles).mock.calls[0][1].expected_wave).toBe(1);
  });

  it("advances battle waves until the turn completes, using each response's version", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("awaiting_commands", 2));
    vi.mocked(simulationApi.advanceBattles)
      .mockResolvedValueOnce(mutation("awaiting_commands", 3))
      .mockResolvedValueOnce(mutation("turn_completed", 4));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("turn_completed"));
    const secondGuard = vi.mocked(simulationApi.advanceBattles).mock.calls[1][1];
    expect(secondGuard.expected_world_version).toBe(3);
  });

  it("stops at a pending scene without advancing further", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("awaiting_scene", 2));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("awaiting_scene"));
    expect(simulationApi.advanceBattles).not.toHaveBeenCalled();
  });

  it("derives and stores turn report in strategyPlay.store when turn completes", async () => {
    useStrategyPlayStore.getState().reset();
    useStrategyPlayStore.setState({ autoShowTurnReport: true });
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("turn_completed", 2));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("turn_completed"));
    expect(useStrategyPlayStore.getState().latestReport).not.toBeNull();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(true);
  });

  it("fetches the report for the turn that just completed and stores the merged result", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue({ ...mutation("turn_completed", 2), turn: 4 });
    vi.mocked(simulationApi.getTurnReport).mockResolvedValue({
      turn: 3,
      net_gold: 42,
      economy: [],
      battles: [],
      lines: [],
      major_event_kinds: [],
    });
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(useStrategyPlayStore.getState().latestReport?.quickStats.netGold).toBe(42));
    expect(simulationApi.getTurnReport).toHaveBeenCalledWith(PLAYTHROUGH_ID, 3);
  });

  it("falls back to the estimated report when the report request fails", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue({ ...mutation("turn_completed", 2), turn: 4 });
    vi.mocked(simulationApi.getTurnReport).mockRejectedValue(new Error("boom"));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(useStrategyPlayStore.getState().latestReport).not.toBeNull());
    expect(useStrategyPlayStore.getState().latestReport?.estimatedSections).toContain("economy_lines");
  });

  it("does not request a report while the turn is still paused", async () => {
    vi.mocked(simulationApi.endTurn).mockResolvedValue(mutation("awaiting_scene", 2));
    const { result } = renderEndTurn();
    act(() => result.current.endTurn());
    await waitFor(() => expect(result.current.lastTurnResult?.status).toBe("awaiting_scene"));
    expect(simulationApi.getTurnReport).not.toHaveBeenCalled();
  });
});
