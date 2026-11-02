import { describe, it, expect } from "vitest";
import { canBesiegeFrom } from "../besiegeEligibility";
import type { ArmyView, CampaignWorldView } from "../../types/simulation.types";

const army: ArmyView = {
  army_id: "army-1",
  owner_id: "me",
  location_id: "reg-enemy",
};

function makeWorld(overrides: Partial<CampaignWorldView> = {}): CampaignWorldView {
  return {
    world_version: 1,
    turn: 1,
    wave: 0,
    status: "planning",
    battles: [],
    clock: { turn: 1, start_year: 1042, start_month: 7 },
    my_faction: {
      id: "me",
      treasury: 0,
      manpower: 0,
      stability: 50,
      war_exhaustion: 0,
      reputation: 0,
      tax_rate: "normal",
      loans: [],
    },
    ruler: { name: "King" },
    regions: [{ region_id: "reg-enemy", owner_id: "foe", terrain: "plain", visibility: "visible" }],
    armies: [army],
    rivals: [{ faction_id: "foe", relation: "war" }] as CampaignWorldView["rivals"],
    queued_orders: [],
    orders_remaining: 3,
    ...overrides,
  };
}

describe("canBesiegeFrom", () => {
  it("allows an own army standing in the region of a faction at war", () => {
    expect(canBesiegeFrom(army, makeWorld())).toBe(true);
  });

  it("refuses an army that is not ours", () => {
    expect(canBesiegeFrom({ ...army, owner_id: "foe" }, makeWorld())).toBe(false);
  });

  it("refuses when the region owner is not at war with us", () => {
    const world = makeWorld({
      rivals: [{ faction_id: "foe", relation: "peace" }] as CampaignWorldView["rivals"],
    });
    expect(canBesiegeFrom(army, world)).toBe(false);
  });

  it("refuses our own region", () => {
    const world = makeWorld({
      regions: [{ region_id: "reg-enemy", owner_id: "me", terrain: "plain", visibility: "visible" }],
    });
    expect(canBesiegeFrom(army, world)).toBe(false);
  });

  it("refuses a region that is already occupied or under siege", () => {
    const occupied = makeWorld({
      regions: [
        {
          region_id: "reg-enemy",
          owner_id: "foe",
          terrain: "plain",
          visibility: "visible",
          occupation: { occupier_id: "me", siege_progress: 100, hold_turns: 0 },
        },
      ],
    });
    const besieged = makeWorld({
      regions: [
        {
          region_id: "reg-enemy",
          owner_id: "foe",
          terrain: "plain",
          visibility: "visible",
          siege: { besieger_id: "me", progress: 30 },
        },
      ],
    });
    expect(canBesiegeFrom(army, occupied)).toBe(false);
    expect(canBesiegeFrom(army, besieged)).toBe(false);
  });
});
