import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { parseCampaignWorld } from "../../lib/campaignWorldParser";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/shared/lib/api-client";
import {
  acceptCommand,
  advanceBattles,
  cancelCommand,
  checkCommand,
  endTurn,
  getBattle,
  getCampaignWorld,
  getStrategyDispatchStreamPath,
  getStrategyDispatches,
  getStrategySummaries,
  getStrategySummary,
  listBattleReports,
  verifyPlaythroughReplay,
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
    mockedClient.get.mockResolvedValueOnce({ data: DEFAULT_PREVIEW_WORLD });
    const result = await getCampaignWorld("playthrough-123");
    expect(mockedClient.get).toHaveBeenCalledWith(`${BASE}/world`, REQUEST_CONFIG);
    expect(result).toEqual(parseCampaignWorld(DEFAULT_PREVIEW_WORLD));
  });

  it("returns a complete CampaignWorldView with diplomacy, vassalage, threats, and endings", async () => {
    const rawWorld = {
      ...DEFAULT_PREVIEW_WORLD,
      alliances: [
        {
          id: "all-1",
          partner_id: "f-oakhaven",
          alliance_type: "defensive" as const,
          ends_turn: 10,
          is_separate_peace_banned: true,
        },
      ],
      vassalages: [
        {
          id: "vas-1",
          overlord_id: "f-valenreach",
          vassal_id: "f-oakhaven",
          tribute_share_percent: 20,
          levy_share_percent: 15,
          is_foreign_policy_controlled: true,
          has_garrison_rights: true,
          ends_turn: 25,
        },
      ],
      coalitions: [
        {
          id: "coalition-1",
          target_id: "f-ironmark",
          member_ids: ["f-valenreach", "f-oakhaven"],
          expires_turn: 8,
        },
      ],
      truces: [
        {
          faction_a: "f-valenreach",
          faction_b: "f-ironmark",
          tier: "short",
          expires_turn: 6,
          is_fragile: false,
          guarantor_ids: [],
        },
      ],
      own_hostages: [
        {
          id: "hos-1",
          giver_id: "f-ironmark",
          holder_id: "f-valenreach",
          leader_id: "ldr-brandon",
          release_turn: 8,
          is_at_mercy: false,
        },
      ],
      open_mediations: [
        {
          id: "med-1",
          mediator_id: "f-highcrag",
          war_id: "war-1",
          expires_turn: 5,
        },
      ],
      subsidies: [
        {
          id: "sub-1",
          payer_id: "f-valenreach",
          receiver_id: "f-oakhaven",
          war_id: "war-1",
          amount_per_turn: 25,
          turns_left: 4,
        },
      ],
      mobilization: { turns_left: 3 },
      pending_calls: [
        {
          id: "call-1",
          caller_id: "f-oakhaven",
          war_id: "war-1",
          side: "defender" as const,
          is_defensive: true,
          deadline_turn: 3,
        },
      ],
      pending_demands: [
        {
          id: "dem-1",
          overlord_id: "f-ironmark",
          kind: "gold" as const,
          amount: 50,
          granted: 0,
          deadline_turn: 4,
        },
      ],
      pending_battles: [
        {
          battle_id: "bat-1",
          region_id: "reg-dunmere",
          attacker_faction_id: "f-ironmark",
          defender_faction_id: "f-valenreach",
        },
      ],
      own_threat: {
        band: "elevated" as const,
        factors: { aggression: 30, border_friction: 15 },
      },
      ending: {
        ending_id: "end-1",
        kind: "victory",
        turn: 12,
        grade: "triumph" as const,
        inputs: { score: 100 },
      },
    };

    mockedClient.get.mockResolvedValueOnce({ data: rawWorld });
    const result = await getCampaignWorld("playthrough-123");

    expect(result.alliances?.[0].alliance_type).toBe("defensive");
    expect(result.vassalages?.[0].is_foreign_policy_controlled).toBe(true);
    expect(result.coalitions?.[0].expires_turn).toBe(8);
    expect(result.truces?.[0].faction_b).toBe("f-ironmark");
    expect(result.own_hostages?.[0].leader_id).toBe("ldr-brandon");
    expect(result.open_mediations?.[0].war_id).toBe("war-1");
    expect(result.subsidies?.[0].amount_per_turn).toBe(25);
    expect(result.mobilization?.turns_left).toBe(3);
    expect(result.pending_calls?.[0].side).toBe("defender");
    expect(result.pending_demands?.[0].kind).toBe("gold");
    expect(result.pending_battles?.[0].battle_id).toBe("bat-1");
    expect(result.own_threat?.band).toBe("elevated");
    expect(result.ending?.grade).toBe("triumph");
  });

  it("rejects an incomplete world instead of passing it on", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: { my_faction: { id: "f1" } } });
    await expect(getCampaignWorld("playthrough-123")).rejects.toThrow("unreadable world");
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

  it("fetches battle view and battle reports", async () => {
    mockedClient.get
      .mockResolvedValueOnce({ data: { id: "b-1" } })
      .mockResolvedValueOnce({ data: { items: [{ exchange_index: 1 }] } });

    const battle = await getBattle("playthrough-123", "b-1");
    const reports = await listBattleReports("playthrough-123", "b-1", 0, 50);

    expect(mockedClient.get).toHaveBeenNthCalledWith(1, `${BASE}/battles/b-1`, REQUEST_CONFIG);
    expect(battle).toEqual({ id: "b-1" });
    expect(reports).toEqual([{ exchange_index: 1 }]);
  });

  it("posts battle field commands with the operation guard and advances battles", async () => {
    mockedClient.post
      .mockResolvedValueOnce({ data: { status: "accepted" } })
      .mockResolvedValueOnce({ data: { turn: 1, wave: 1 } });
    const command = {
      kind: "commit_reserves",
      faction_id: "f1",
      battle_id: "b1",
    } as const;

    const commandRes = await acceptCommand("playthrough-123", command, guard);
    const advanceRes = await advanceBattles("playthrough-123", guard);

    expect(mockedClient.post).toHaveBeenNthCalledWith(
      1,
      `${BASE}/commands`,
      { ...guard, command },
      REQUEST_CONFIG,
    );
    expect(mockedClient.post).toHaveBeenNthCalledWith(
      2,
      `${BASE}/battles/advance`,
      guard,
      REQUEST_CONFIG,
    );
    expect(commandRes).toEqual({ status: "accepted" });
    expect(advanceRes).toEqual({ turn: 1, wave: 1 });
  });
});

describe("dispatch api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists spymaster dispatches for a playthrough", async () => {
    mockedClient.get.mockResolvedValueOnce({ data: [] });
    const result = await getStrategyDispatches("playthrough-123");
    expect(mockedClient.get).toHaveBeenCalledWith(`${BASE}/dispatches`, REQUEST_CONFIG);
    expect(result).toEqual([]);
  });

  it("builds the dispatch stream path through the TRS proxy", () => {
    expect(getStrategyDispatchStreamPath("playthrough-123", "rumor_4")).toBe(
      "/trs/v1/strategy/playthroughs/playthrough-123/dispatches/rumor_4/stream",
    );
  });
});

describe("replay verification api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts to replay verify without through_turn", async () => {
    const payload = {
      verified_turn: 3,
      world_hash: "a".repeat(64),
      step_count: 12,
    };
    mockedClient.post.mockResolvedValueOnce({ data: payload });

    const result = await verifyPlaythroughReplay("playthrough-123");
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/replay/verify`,
      undefined,
      REQUEST_CONFIG,
    );
    expect(result).toEqual(payload);
  });

  it("posts to replay verify with through_turn query parameter", async () => {
    const payload = {
      verified_turn: 1,
      world_hash: "b".repeat(64),
      step_count: 5,
    };
    mockedClient.post.mockResolvedValueOnce({ data: payload });

    const result = await verifyPlaythroughReplay("playthrough-123", 1);
    expect(mockedClient.post).toHaveBeenCalledWith(
      `${BASE}/replay/verify?through_turn=1`,
      undefined,
      REQUEST_CONFIG,
    );
    expect(result).toEqual(payload);
  });
});
