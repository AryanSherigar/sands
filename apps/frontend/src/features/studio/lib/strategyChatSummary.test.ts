import { describe, expect, it } from "vitest";
import type { ActionBlock, AssistantStrategyContextPayload } from "../types/assistant.types";
import { describeStrategyBlock } from "./strategyChatSummary";

const context: AssistantStrategyContextPayload = {
  title: "The Reach",
  timing: { start_year: 1000, start_month: 1, end_year: 1010 },
  factions: [
    {
      faction_id: "ashford",
      name: "Ashford",
      leader_id: "ashford_ruler",
      leader_name: "Lord Edric",
      leader_history: "",
      capital_region_id: null,
      treasury: 100,
      manpower: 100,
      stability: 50,
      is_playable: true,
    },
  ],
  regions: [
    { region_id: "north", name: "North Reach", owner_id: null, population: 0, wealth: 0, manpower: 0, unrest: 0, garrison: 0 },
  ],
  relations: [],
  claims: [],
  grudges: [],
  armies: [],
  rules: {},
  active_panel: "",
};

const block = (target: ActionBlock["target"], body: unknown): ActionBlock => ({
  target,
  content: JSON.stringify(body),
});

describe("describeStrategyBlock", () => {
  it("names factions, rulers and regions instead of showing ids", () => {
    const claim = describeStrategyBlock(block("claim", { faction_id: "ashford", region_id: "north" }), context, []);
    const army = describeStrategyBlock(
      block("army", { owner_id: "ashford", location_id: "north", troops: { infantry: 300, archers_siege: 50 } }),
      context,
      [],
    );

    expect(claim).toBe("Ashford claims North Reach");
    expect(army).toBe("Ashford army at North Reach: 300 infantry, 50 archers/siege");
  });

  it("resolves a faction and ruler created earlier in the same reply", () => {
    const earlier = [block("faction", { temp_id: "east", name: "Eastmark", leader_name: "Queen Ilse" })];

    const relation = describeStrategyBlock(block("relation", { faction_a: "east", faction_b: "ashford", status: "war" }), context, earlier);
    const grudge = describeStrategyBlock(
      block("grudge", { holder_id: "east_ruler", target_id: "ashford_ruler", opinion: -40 }),
      context,
      earlier,
    );

    expect(relation).toBe("Eastmark and Ashford: war");
    expect(grudge).toBe("Queen Ilse resents Lord Edric (opinion -40)");
  });

  it("describes new factions, region changes, timing, rules and titles", () => {
    expect(describeStrategyBlock(block("faction", { name: "Eastmark", leader_name: "Queen Ilse", capital_region_id: "north" }), context, [])).toBe(
      "Found Eastmark, ruled by Queen Ilse, capital North Reach",
    );
    expect(describeStrategyBlock(block("region_setup", { region_id: "north", owner_id: "ashford", unrest: 10 }), context, [])).toBe(
      "North Reach: owner Ashford; sets unrest",
    );
    expect(describeStrategyBlock(block("timing", { start_year: 1200, end_year: 1210 }), context, [])).toBe("Timeline from year 1200 to year 1210");
    expect(describeStrategyBlock(block("rules", { letters_enabled: true }), context, [])).toBe("Rules: letters_enabled");
    expect(describeStrategyBlock({ target: "title", content: " New Name " }, context, [])).toBe('Rename the scenario to "New Name"');
  });

  it("falls back to the raw id when it is unknown and returns null for unreadable data", () => {
    expect(describeStrategyBlock(block("claim", { faction_id: "ghost", region_id: "north" }), context, [])).toBe("ghost claims North Reach");
    expect(describeStrategyBlock({ target: "claim", content: "{nope" }, context, [])).toBeNull();
  });
});
