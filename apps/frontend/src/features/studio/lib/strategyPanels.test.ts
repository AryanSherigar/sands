import { describe, expect, it } from "vitest";
import { addFaction, readStrategyFields, setRegionOwner } from "./strategyDocument";
import { panelForIssue, summarizePanel } from "./strategyPanels";

const issue = (code: string, path: string) => ({ code, path, message: "m" });

describe("panelForIssue", () => {
  it.each([
    ["faction_has_no_army", "factions[0]", "armies"],
    ["faction_has_no_economy", "factions[0]", "region_economy"],
    ["dangling_reference", "starting.relations[0].faction_a", "relations"],
    ["dangling_reference", "starting.armies[1].location_id", "armies"],
    ["dangling_reference", "starting.claims[0].region_id", "claims_grudges"],
    ["dangling_reference", "starting.grudges[0].holder_id", "claims_grudges"],
    ["invalid_vassalage", "starting.relations[2]", "relations"],
    ["faction_has_no_region", "factions[0]", null],
  ])("maps %s at %s to %s", (code, path, expected) => {
    expect(panelForIssue(issue(code, path))).toBe(expected);
  });
});

describe("summarizePanel", () => {
  const fields = setRegionOwner(addFaction(addFaction(readStrategyFields({}), "Ashford"), "Carrow"), "north", "ashford");

  it("summarizes each panel in one line", () => {
    expect(summarizePanel("timeline", fields)).toBe("1000-03 to 1004");
    expect(summarizePanel("region_economy", fields)).toBe("1 region with an economy");
    expect(summarizePanel("armies", fields)).toBe("1 army");
    expect(summarizePanel("relations", fields)).toBe("All at peace");
    expect(summarizePanel("claims_grudges", fields)).toBe("Using defaults");
  });
});
