import { describe, expect, it } from "vitest";
import { computeToolsInUse, type ToolsInUseInput } from "./toolsInUse";

const EMPTY: ToolsInUseInput = {
  stateSchema: {},
  conditions: [],
  sheetRuleCount: 0,
  ruleCheckCount: 0,
  minigames: [],
};

describe("computeToolsInUse", () => {
  it("is empty for a story with nothing that needs a tool", () => {
    expect(computeToolsInUse(EMPTY).size).toBe(0);
  });

  it("needs the status HUD for a value shown on screen, at any depth", () => {
    const display = { kind: "meter", label: "Health", clamp_min: 0, clamp_max: 10 };
    expect(computeToolsInUse({ ...EMPTY, stateSchema: { health: { type: "number", display } } })).toEqual(
      new Set(["status_hud"]),
    );
    const nested = { player: { type: "object" as const, fields: { health: { type: "number" as const, display } } } };
    expect(computeToolsInUse({ ...EMPTY, stateSchema: nested })).toEqual(new Set(["status_hud"]));
  });

  it("needs the HUD for a number shown to the player even with no display hint", () => {
    expect(computeToolsInUse({ ...EMPTY, stateSchema: { oil: { type: "number" } } })).toEqual(new Set(["status_hud"]));
  });

  it("does not need the HUD for hidden numbers or values that are not numbers", () => {
    const stateSchema = {
      oil: { type: "number" as const, hidden: true },
      has_key: { type: "boolean" as const },
    };
    expect(computeToolsInUse({ ...EMPTY, stateSchema }).size).toBe(0);
  });

  it("needs atmosphere, and therefore the HUD it requires, for a rule with a sound", () => {
    const tools = computeToolsInUse({ ...EMPTY, conditions: [{ sensory_cue: "heartbeat" }, { sensory_cue: null }] });
    expect(tools).toEqual(new Set(["atmosphere", "status_hud"]));
  });

  it("maps rule sheet rows, rule checks and the rhythm game to their tools", () => {
    const tools = computeToolsInUse({
      ...EMPTY,
      sheetRuleCount: 2,
      ruleCheckCount: 1,
      minigames: [{ minigame_type: "dodge" }, { minigame_type: "rhythm_composure" }],
    });
    expect(tools).toEqual(new Set(["rule_sheet", "rule_checks", "composure"]));
  });

  it("ignores minigames other than the rhythm game", () => {
    expect(computeToolsInUse({ ...EMPTY, minigames: [{ minigame_type: "lockpick" }] }).size).toBe(0);
  });
});
