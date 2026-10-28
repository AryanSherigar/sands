import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/shared/lib/api-client";
import {
  acceptCommand,
  advanceBattles,
  cancelCommand,
  checkCommand,
  endTurn,
  getCampaignWorld,
  getStrategySummaries,
  getStrategySummary,
} from "../simulation.api";
import type { OperationGuard, StrategyOrder } from "../../types/simulation.types";

vi.mock("@/shared/lib/api-client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);
const BASE = "/simulation/v1/playthroughs/playthrough-123";
const REQUEST_CONFIG = { baseURL: "" };

const guard: OperationGuard = {
  operation_id: "op-1",
  expected_world_version: 4,
  expected_turn: 2,
  expected_wave: 0,
};

const haltOrder: StrategyOrder = { kind: "halt_army", faction_id: "f1", army_id: "a1" };

describe("simulation.api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches the campaign world view", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { my_faction: { id: "f1" } } });
    const result = await getCampaignWorld("playthrough-123");
    expect(mockedClient.get).toHaveBeenCalledWith(`${BASE}/world`, REQUEST_CONFIG);
    expect(result).toEqual({ my_faction: { id: "f1" } });
  });

  it("checks a command without an operation guard", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { orders_remaining: 3 } });
    const result = await checkCommand("playthrough-123", haltOrder);
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/commands/check`,
      { command: haltOrder },
      REQUEST_CONFIG,
    );
    expect(result).toEqual({ orders_remaining: 3 });
  });

  it("accepts a command with the operation guard", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { accepted_command_id: "c1" } });
    const result = await acceptCommand("playthrough-123", haltOrder, guard);
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/commands`,
      { ...guard, command: haltOrder },
      REQUEST_CONFIG,
    );
    expect(result).toEqual({ accepted_command_id: "c1" });
  });

  it("cancels a command with the operation guard", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { status: "planning" } });
    await cancelCommand("playthrough-123", "cmd-1", guard);
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/commands/cmd-1/cancel`,
      guard,
      REQUEST_CONFIG,
    );
  });

  it("ends the turn with the operation guard", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { status: "turn_completed" } });
    const result = await endTurn("playthrough-123", guard);
    expect(mockedClient.post).toHaveBeenCalledWith(`${BASE}/end-turn`, guard, REQUEST_CONFIG);
    expect(result).toEqual({ status: "turn_completed" });
  });

  it("advances battles with the operation guard", async () => {
    mockedClient.post.mockResolvedValueOnce({ data: { status: "awaiting_commands" } });
    await advanceBattles("playthrough-123", guard);
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/battles/advance`,
      guard,
      REQUEST_CONFIG,
    );
  });

  it("fetches durable chronicle history and a selected entry", async () => {
    mockedClient.get
      .mockResolvedValueOnce({ data: { items: [] } })
      .mockResolvedValueOnce({ data: { summary_id: "summary-1", status: "pending" } });

    await expect(getStrategySummaries("playthrough-123")).resolves.toEqual({ items: [] });
    await expect(getStrategySummary("playthrough-123", "summary-1")).resolves.toEqual({
      summary_id: "summary-1",
      status: "pending",
    });
    expect(mockedClient.get).toHaveBeenNthCalledWith(
      1,
      `${BASE}/summaries`,
      REQUEST_CONFIG,
    );
    expect(mockedClient.get).toHaveBeenNthCalledWith(
      2,
      `${BASE}/summaries/summary-1`,
      REQUEST_CONFIG,
    );
  });
});
