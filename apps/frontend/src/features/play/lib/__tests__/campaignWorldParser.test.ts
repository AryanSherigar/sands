import { describe, expect, it } from "vitest";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { parseCampaignWorld } from "../campaignWorldParser";

describe("parseCampaignWorld", () => {
  it("accepts a complete world and defaults battles to empty", () => {
    const { battles: _battles, ...payload } = DEFAULT_PREVIEW_WORLD;

    expect(parseCampaignWorld(payload).battles).toEqual([]);
  });

  it("restores in-flight battles from pending_battles after a reload", () => {
    const { battles: _battles, ...payload } = DEFAULT_PREVIEW_WORLD;
    const world = parseCampaignWorld({
      ...payload,
      pending_battles: [
        {
          id: "battle-1",
          region_id: "reg-a",
          status: "awaiting_commands",
          control_mode: "player",
          exchanges_used: 1,
          total_exchanges: 1,
          is_big: true,
          current_turn: 3,
        },
        { not: "a battle" },
      ],
    });

    expect(world.battles).toEqual([
      expect.objectContaining({ id: "battle-1", control_mode: "player", status: "awaiting_commands" }),
    ]);
  });

  it("prefers battles already on the payload over pending_battles", () => {
    const payload = {
      ...DEFAULT_PREVIEW_WORLD,
      battles: [{ id: "b-live", region_id: "r", status: "awaiting_commands", exchanges_used: 0, total_exchanges: 0 }],
      pending_battles: [{ id: "b-old", region_id: "r" }],
    };

    expect(parseCampaignWorld(payload).battles.map((battle) => battle.id)).toEqual(["b-live"]);
  });

  it("rejects a payload that is not an object", () => {
    expect(() => parseCampaignWorld(null)).toThrow("unreadable world");
  });

  it("names the first missing field instead of inventing data", () => {
    const { regions: _regions, ...payload } = DEFAULT_PREVIEW_WORLD;

    expect(() => parseCampaignWorld(payload)).toThrow("missing regions");
  });

  it("defaults optional array fields to empty arrays when omitted", () => {
    const { battles: _battles, ...payload } = DEFAULT_PREVIEW_WORLD;
    const world = parseCampaignWorld(payload);

    expect(world.battles).toEqual([]);
    expect(world.pending_demands).toEqual([]);
    expect(world.pending_calls).toEqual([]);
    expect(world.alliances).toEqual([]);
    expect(world.vassalages).toEqual([]);
    expect(world.coalitions).toEqual([]);
    expect(world.truces).toEqual([]);
    expect(world.own_hostages).toEqual([]);
    expect(world.open_mediations).toEqual([]);
    expect(world.subsidies).toEqual([]);
  });

  it("preserves existing collections in optional array fields", () => {
    const payload = {
      ...DEFAULT_PREVIEW_WORLD,
      alliances: [{ id: "alliance-1" }],
    };
    const world = parseCampaignWorld(payload);

    expect(world.alliances).toEqual([{ id: "alliance-1" }]);
  });
});
