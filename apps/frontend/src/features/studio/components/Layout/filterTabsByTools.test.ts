import { describe, expect, it } from "vitest";
import type { ToolKey } from "@/shared/constants/scenario-tools";
import { filterTabsByTools, isTabAvailable } from "./filterTabsByTools";

const TABS: readonly { id: string; label: string; tool?: ToolKey }[] = [
  { id: "entities", label: "Entities" },
  { id: "checks", label: "Rule checks", tool: "rule_checks" },
  { id: "hud", label: "HUD", tool: "status_hud" },
];

describe("filterTabsByTools", () => {
  it("keeps only tabs that need no tool when none are enabled", () => {
    expect(filterTabsByTools(TABS, []).map((tab) => tab.id)).toEqual(["entities"]);
  });

  it("adds a tool's tab when that tool is enabled", () => {
    expect(
      filterTabsByTools(TABS, ["rule_checks"]).map((tab) => tab.id),
    ).toEqual(["entities", "checks"]);
  });

  it("keeps the original order", () => {
    expect(
      filterTabsByTools(TABS, ["status_hud", "rule_checks"]).map((tab) => tab.id),
    ).toEqual(["entities", "checks", "hud"]);
  });
});

describe("isTabAvailable", () => {
  it("is true for tool-free tabs and enabled tools only", () => {
    expect(isTabAvailable({}, [])).toBe(true);
    expect(isTabAvailable({ tool: "status_hud" }, [])).toBe(false);
    expect(isTabAvailable({ tool: "status_hud" }, ["status_hud"])).toBe(true);
  });
});
