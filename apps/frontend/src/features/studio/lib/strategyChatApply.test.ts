import { describe, expect, it } from "vitest";
import type { ActionBlock } from "../types/assistant.types";
import { applyStrategyBlock, type StrategyApplyContext } from "./strategyChatApply";
import { addFaction, readStrategyFields } from "./strategyDocument";

const twoFactions = addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow");

const makeContext = (): StrategyApplyContext => ({
  knownRegionIds: new Set(["north", "south"]),
  tempFactionIds: new Map(),
});

const block = (target: ActionBlock["target"], body: unknown): ActionBlock => ({
  target,
  content: JSON.stringify(body),
});

describe("applyStrategyBlock", () => {
  it("adds a faction with its ruler and records the temp id for later blocks", () => {
    const context = makeContext();
    const created = applyStrategyBlock(
      twoFactions,
      block("faction", { temp_id: "east", name: "Eastmark", leader_name: "Queen Ilse", treasury: 250, capital_region_id: "north" }),
      context,
    );

    expect(created.error).toBeNull();
    const faction = created.fields.factions.find((item) => item.name === "Eastmark");
    expect(faction).toMatchObject({ treasury: 250, capital_region_id: "north" });
    expect(created.fields.leaders.find((item) => item.id === faction?.leader_id)?.name).toBe("Queen Ilse");

    const claimed = applyStrategyBlock(created.fields, block("claim", { faction_id: "east", region_id: "south" }), context);
    expect(claimed.error).toBeNull();
    expect(claimed.fields.claims).toEqual([{ faction_id: faction?.id, region_id: "south" }]);
  });

  it("sets a relation between two existing factions", () => {
    const result = applyStrategyBlock(
      twoFactions,
      block("relation", { faction_a: "ashford", faction_b: "carrow", status: "war" }),
      makeContext(),
    );

    expect(result.error).toBeNull();
    expect(result.fields.relations[0].status).toBe("war");
  });

  it("rejects an unknown faction without changing the fields", () => {
    const result = applyStrategyBlock(
      twoFactions,
      block("relation", { faction_a: "ashford", faction_b: "ghost", status: "war" }),
      makeContext(),
    );

    expect(result.error).not.toBeNull();
    expect(result.fields).toBe(twoFactions);
  });

  it("rejects a claim on a region that is not on the map", () => {
    const result = applyStrategyBlock(twoFactions, block("claim", { faction_id: "ashford", region_id: "atlantis" }), makeContext());

    expect(result.error).not.toBeNull();
    expect(result.fields.claims).toEqual([]);
  });

  it("sets region owner and economy, clamping unrest to 100", () => {
    const result = applyStrategyBlock(
      twoFactions,
      block("region_setup", { region_id: "north", owner_id: "ashford", population: 900, unrest: 400 }),
      makeContext(),
    );

    expect(result.error).toBeNull();
    expect(result.fields.regions.find((item) => item.region_id === "north")).toMatchObject({
      owner_id: "ashford",
      population: 900,
      unrest: 100,
    });
  });

  it("adds an army with troops and a named commander", () => {
    const result = applyStrategyBlock(
      twoFactions,
      block("army", { owner_id: "carrow", location_id: "south", troops: { cavalry: 120, dragons: 9 }, commander_name: "Sir Orrin" }),
      makeContext(),
    );

    expect(result.error).toBeNull();
    const army = result.fields.armies[0];
    expect(army.troops).toEqual({ cavalry: 120 });
    expect(result.fields.commanders.find((item) => item.id === army.commander_id)?.name).toBe("Sir Orrin");
  });

  it("writes a grudge between two rulers", () => {
    const [first, second] = twoFactions.leaders;
    const result = applyStrategyBlock(
      twoFactions,
      block("grudge", { holder_id: first.id, target_id: second.id, opinion: -60, reason: "Burned the granaries" }),
      makeContext(),
    );

    expect(result.error).toBeNull();
    expect(result.fields.grudges[0]).toMatchObject({ opinion: -60, reason: "Burned the granaries" });
  });

  it("updates a ruler's history", () => {
    const leader = twoFactions.leaders[0];
    const result = applyStrategyBlock(twoFactions, block("leader_history", { leader_id: leader.id, history: "Raised in exile." }), makeContext());

    expect(result.fields.leaders[0].history).toBe("Raised in exile.");
  });

  it("applies timing and only the supplied rules", () => {
    const timed = applyStrategyBlock(twoFactions, block("timing", { start_year: 1200, start_month: 6, end_year: 1210 }), makeContext());
    const ruled = applyStrategyBlock(timed.fields, block("rules", { agents_enabled: true, conditional_gate_percent: 999 }), makeContext());

    expect(timed.fields.timing).toEqual({ start_year: 1200, start_month: 6, end_year: 1210 });
    expect(ruled.fields.rules.agents_enabled).toBe(true);
    expect(ruled.fields.rules.conditional_gate_percent).toBeLessThanOrEqual(200);
    expect(ruled.fields.rules.bribe_base_price).toBe(twoFactions.rules.bribe_base_price);
  });

  it("reports unreadable JSON and unsupported targets", () => {
    const broken = applyStrategyBlock(twoFactions, { target: "claim", content: "{nope" }, makeContext());
    const unsupported = applyStrategyBlock(twoFactions, block("lore", {}), makeContext());

    expect(broken.error).toMatch(/invalid data/);
    expect(unsupported.error).not.toBeNull();
  });

  it("does not add a second faction when the same one is applied again", () => {
    const body = { temp_id: "east", name: "Eastmark", treasury: 250 };
    const first = applyStrategyBlock(twoFactions, block("faction", body), makeContext());
    const again = applyStrategyBlock(first.fields, block("faction", body), makeContext());

    expect(again.error).toBeNull();
    expect(again.fields.factions.filter((item) => item.name === "Eastmark")).toHaveLength(1);
    expect(again.fields.leaders).toHaveLength(first.fields.leaders.length);
  });

  it("does not add an identical army twice", () => {
    const body = { owner_id: "ashford", location_id: "north", troops: { infantry: 300 } };
    const first = applyStrategyBlock(twoFactions, block("army", body), makeContext());
    const again = applyStrategyBlock(first.fields, block("army", body), makeContext());

    expect(first.fields.armies).toHaveLength(1);
    expect(again.fields.armies).toHaveLength(1);
  });

  it("lets a grudge name the ruler of a faction created in the same reply", () => {
    const context = makeContext();
    const created = applyStrategyBlock(twoFactions, block("faction", { temp_id: "east", name: "Eastmark", leader_name: "Queen Ilse" }), context);
    const carrowRuler = created.fields.factions.find((item) => item.id === "carrow")?.leader_id;
    const grudge = applyStrategyBlock(
      created.fields,
      block("grudge", { holder_id: "east_ruler", target_id: carrowRuler, opinion: -40 }),
      context,
    );

    const eastRuler = created.fields.factions.find((item) => item.name === "Eastmark")?.leader_id;
    expect(grudge.error).toBeNull();
    expect(grudge.fields.grudges[0]).toMatchObject({ holder_id: eastRuler, opinion: -40 });
  });

  it("applies the letters and judgments rules", () => {
    const ruled = applyStrategyBlock(
      twoFactions,
      block("rules", { letters_enabled: true, judgment_sentence_turns: 3 }),
      makeContext(),
    );

    expect(ruled.fields.rules).toMatchObject({ letters_enabled: true, judgment_sentence_turns: 3 });
  });
});
