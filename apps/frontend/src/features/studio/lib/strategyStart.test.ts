import { describe, expect, it } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { addFaction, applyStrategyFields, readStrategyFields, removeFaction, setRegionOwner, updateFaction } from "./strategyDocument";
import {
  addArmy,
  addClaim,
  addGrudge,
  applyPreset,
  clampWholeNumber,
  countTurns,
  removeArmy,
  removeClaim,
  removeGrudge,
  setRelation,
  setTiming,
  setVassalage,
  updateArmy,
  updateGrudge,
  updateRegionEconomy,
} from "./strategyStart";

const twoFactions = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");

describe("clampWholeNumber", () => {
  it.each([
    ["", undefined, 0],
    ["-5", undefined, 0],
    ["3.7", undefined, 3],
    ["abc", undefined, 0],
    ["150", 100, 100],
    [42, undefined, 42],
  ])("clamps %j (max %j) to %j", (raw, max, expected) => {
    expect(clampWholeNumber(raw, max)).toBe(expected);
  });
});

describe("timing", () => {
  it("defaults the end year to the Studio default only when absent", () => {
    expect(readStrategyFields({}).timing).toEqual({ start_year: 1000, start_month: 3, end_year: 1004 });
    expect(readStrategyFields({ tuning: { end_year: 1030 } }).timing.end_year).toBe(1030);
  });

  it("keeps the end year after the start year and the month in range", () => {
    expect(setTiming(twoFactions, { end_year: 1000 }).timing.end_year).toBe(1001);
    expect(setTiming(twoFactions, { start_year: 1010 }).timing.end_year).toBe(1011);
    expect(setTiming(twoFactions, { start_month: 15 }).timing.start_month).toBe(12);
  });
});

describe("region economy and owner seeding", () => {
  it("seeds economy and a starter army when a region first gets an owner", () => {
    const fields = setRegionOwner(twoFactions, "north", "ashford");
    expect(fields.regions[0]).toMatchObject({ region_id: "north", owner_id: "ashford", wealth: 50 });
    expect(fields.armies).toHaveLength(1);
    expect(fields.armies[0]).toMatchObject({ owner_id: "ashford", location_id: "north", morale: 70 });
  });

  it("leaves edited economy and existing armies alone on re-assignment", () => {
    const seeded = setRegionOwner(twoFactions, "north", "ashford");
    const edited = updateRegionEconomy(seeded, "north", { wealth: 7 });
    const moved = setRegionOwner(setRegionOwner(edited, "north", null), "north", "ashford");
    expect(moved.regions[0].wealth).toBe(7);
    expect(moved.armies).toHaveLength(1);
  });

  it("clamps unrest to a percent", () => {
    const fields = updateRegionEconomy(twoFactions, "north", { unrest: 300 });
    expect(fields.regions[0].unrest).toBe(100);
  });
});

describe("armies", () => {
  it("adds, updates and removes an army with unique ids", () => {
    const added = addArmy(addArmy(twoFactions, "ashford", "north"), "ashford", "south");
    expect(added.armies.map((item) => item.id)).toEqual(["ashford_army", "ashford_army_2"]);
    const updated = updateArmy(added, "ashford_army", { troops: { infantry: 500 } });
    expect(updated.armies[0].troops.infantry).toBe(500);
    expect(removeArmy(updated, "ashford_army").armies).toHaveLength(1);
  });
});

describe("relations", () => {
  it("adds explicit peace between every pair of factions", () => {
    expect(twoFactions.relations).toEqual([
      { faction_a: "ashford", faction_b: "carrow", status: "peace", vassalage: null },
    ]);
  });

  it("ignores a self pair and keeps one entry per unordered pair", () => {
    expect(setRelation(twoFactions, "ashford", "ashford", "war")).toBe(twoFactions);
    const once = setRelation(twoFactions, "ashford", "carrow", "war");
    const twice = setRelation(once, "carrow", "ashford", "alliance");
    expect(twice.relations).toHaveLength(1);
    expect(twice.relations[0].status).toBe("alliance");
  });

  it("creates a vassalage only on peace and clears it when the status changes", () => {
    const vassal = setVassalage(twoFactions, "ashford", "carrow", "ashford");
    expect(vassal.relations[0].vassalage).toMatchObject({ overlord_id: "ashford", tribute_share_percent: 20 });
    expect(setVassalage(vassal, "ashford", "carrow", "stranger")).toBe(vassal);
    expect(setRelation(vassal, "ashford", "carrow", "war").relations[0].vassalage).toBeNull();
    expect(setVassalage(vassal, "ashford", "carrow", null).relations[0].vassalage).toBeNull();
  });

  it("refuses a vassalage on a pair at war", () => {
    const war = setRelation(twoFactions, "ashford", "carrow", "war");
    expect(setVassalage(war, "ashford", "carrow", "ashford")).toBe(war);
  });
});

describe("claims and grudges", () => {
  it("ignores a duplicate claim and removes one", () => {
    const once = addClaim(twoFactions, "ashford", "north");
    expect(addClaim(once, "ashford", "north")).toBe(once);
    expect(removeClaim(once, "ashford", "north").claims).toEqual([]);
  });

  it("rejects a self grudge and a duplicate pair, and clamps opinion", () => {
    expect(addGrudge(twoFactions, "ashford_ruler", "ashford_ruler")).toBe(twoFactions);
    const once = addGrudge(twoFactions, "ashford_ruler", "carrow_ruler");
    expect(once.grudges[0]).toMatchObject({ opinion: -50, reason: "" });
    expect(addGrudge(once, "ashford_ruler", "carrow_ruler")).toBe(once);
    const tuned = updateGrudge(once, "ashford_ruler", "carrow_ruler", { opinion: -400 });
    expect(tuned.grudges[0].opinion).toBe(-100);
    expect(removeGrudge(tuned, "ashford_ruler", "carrow_ruler").grudges).toEqual([]);
  });
});

describe("removing a faction cascades", () => {
  it("drops its armies, relations, claims and grudges", () => {
    let fields = setRegionOwner(twoFactions, "north", "ashford");
    fields = addClaim(fields, "ashford", "south");
    fields = addGrudge(fields, "carrow_ruler", "ashford_ruler");
    const removed = removeFaction(fields, "ashford");
    expect(removed.armies).toEqual([]);
    expect(removed.relations).toEqual([]);
    expect(removed.claims).toEqual([]);
    expect(removed.grudges).toEqual([]);
  });
});

describe("document round trip", () => {
  it("preserves unknown keys in starting, tuning and region setups", () => {
    const document = {
      starting: {
        regions: [
          { region_id: "north", owner_id: "ashford", population: 1, wealth: 2, manpower: 3, unrest: 4, garrison: 5, faith_id: "old" },
        ],
        armies: [],
        relations: [],
        claims: [],
        grudges: [],
        extra: 1,
      },
      tuning: { orders_per_turn: 4, start_year: 1000, start_month: 3, end_year: 1004 },
      factions: [],
      leaders: [],
      ambitions: [],
      commanders: [],
    };
    expect(applyStrategyFields(document, readStrategyFields(document))).toEqual(document);
  });
});

describe("countTurns", () => {
  it("matches the readiness-plan example: 1000-03 to 1004 is 29 turns", () => {
    expect(countTurns({ start_year: 1000, start_month: 3, end_year: 1004 })).toBe(29);
  });

  it("counts a January start", () => {
    expect(countTurns({ start_year: 1000, start_month: 1, end_year: 1000 })).toBe(6);
  });
});

describe("applyPreset", () => {
  const makeRegion = (id: string, neighborIds: string[]): MapRegion => ({
    id, name: id, terrain: "plain", outline: "M0 0", label_point: { x: 0, y: 0 }, neighbor_ids: neighborIds, source_color: null, source_ref: null,
  });
  const map = [
    makeRegion("north", ["mid"]),
    makeRegion("mid", ["north", "midb"]),
    makeRegion("midb", ["mid", "south"]),
    makeRegion("south", ["midb"]),
  ];
  const owners: [string, string][] = [["north", "ashford"], ["mid", "ashford"], ["midb", "carrow"], ["south", "carrow"]];
  const world = owners.reduce((acc, [region, owner]) => setRegionOwner(acc, region, owner), twoFactions);
  const capitals = updateFaction(updateFaction(world, "ashford", { capital_region_id: "north" }), "carrow", { capital_region_id: "south" });

  it("peaceful: all pairs at peace and one army per faction in its capital", () => {
    const warring = setRelation(capitals, "ashford", "carrow", "war");
    const result = applyPreset(warring, "peaceful", map);
    expect(result.relations.map((item) => item.status)).toEqual(["peace"]);
    expect(result.armies.map((item) => [item.owner_id, item.location_id])).toEqual([["ashford", "north"], ["carrow", "south"]]);
  });

  it("border_war: first two factions at war with an army on each side of the border", () => {
    const result = applyPreset(capitals, "border_war", map);
    expect(result.relations[0].status).toBe("war");
    const locations = result.armies.map((item) => `${item.owner_id}@${item.location_id}`);
    expect(locations).toEqual(expect.arrayContaining(["ashford@north", "ashford@mid", "carrow@south", "carrow@midb"]));
  });
});
