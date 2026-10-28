import { describe, expect, it } from "vitest";
import {
  SCENARIO_TOOLS,
  TOOL_KEYS,
  getEnabledDependents,
  isToolKey,
} from "../scenario-tools";

describe("scenario tools constants", () => {
  it("declares a definition for every tool key, in order", () => {
    expect(SCENARIO_TOOLS.map((tool) => tool.key)).toEqual([...TOOL_KEYS]);
  });

  it("only requires known tool keys", () => {
    for (const tool of SCENARIO_TOOLS) {
      for (const required of tool.requires) {
        expect(isToolKey(required)).toBe(true);
      }
    }
  });

  it("recognises tool keys and rejects strangers", () => {
    expect(isToolKey("rule_checks")).toBe(true);
    expect(isToolKey("teleporter")).toBe(false);
  });

  it("lists enabled tools that depend on a key", () => {
    expect(getEnabledDependents("status_hud", ["status_hud", "atmosphere"])).toEqual(
      ["atmosphere"],
    );
  });

  it("reports no dependents when the dependent tool is off", () => {
    expect(getEnabledDependents("status_hud", ["status_hud"])).toEqual([]);
  });
});
