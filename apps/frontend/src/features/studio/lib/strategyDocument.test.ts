import { describe, expect, it } from "vitest";
import {
  addFaction,
  applyStrategyFields,
  getRegionOwner,
  makeUniqueId,
  readStrategyFields,
  removeFaction,
  setLeaderAmbitionPreset,
  setRegionOwner,
} from "./strategyDocument";

const empty = readStrategyFields({});

describe("strategyDocument", () => {
  it("builds a unique valid id from a name", () => {
    expect(makeUniqueId("House Ashford!", [])).toBe("house_ashford");
    expect(makeUniqueId("House Ashford", ["house_ashford"])).toBe("house_ashford_2");
    expect(makeUniqueId("7th Host", [])).toBe("f_7th_host");
  });

  it("adds a faction with a ready leader and ambition, first one playable", () => {
    const fields = addFaction(addFaction(empty, "Ashford"), "Carrow");

    expect(fields.factions.map((item) => item.is_playable)).toEqual([true, false]);
    expect(fields.leaders[0].faction_id).toBe("ashford");
    expect(fields.leaders[0].ambition_ids).toEqual(["ashford_expand"]);
    expect(fields.leaders[0].trait_ids).toHaveLength(2);
    expect(fields.ambitions[0].condition.subject_id).toBe("ashford");
  });

  it("switches a leader's ambition preset without leaving the old one behind", () => {
    const fields = setLeaderAmbitionPreset(addFaction(empty, "Ashford"), "ashford_ruler", "rich");

    expect(fields.ambitions.map((item) => item.id)).toEqual(["ashford_rich"]);
    expect(fields.leaders[0].ambition_ids).toEqual(["ashford_rich"]);
  });

  it("removes a faction with its leader, ambition and region ownership", () => {
    const owned = setRegionOwner(addFaction(empty, "Ashford"), "north", "ashford");
    const fields = removeFaction(owned, "ashford");

    expect(fields.factions).toEqual([]);
    expect(fields.leaders).toEqual([]);
    expect(fields.ambitions).toEqual([]);
    expect(getRegionOwner(fields, "north")).toBeNull();
  });

  it("keeps untouched document keys when applying edits", () => {
    const raw = { map: { regions: [] }, starting: { armies: [1] }, theme: { a: 1 } };
    const applied = applyStrategyFields(raw, addFaction(readStrategyFields(raw), "Ashford"));

    expect(applied.map).toEqual(raw.map);
    expect(applied.theme).toEqual(raw.theme);
    expect((applied.starting as { armies: number[] }).armies).toEqual([1]);
  });
});
