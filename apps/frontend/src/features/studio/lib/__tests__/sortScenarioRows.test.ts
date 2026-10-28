import { describe, expect, it } from "vitest";
import type { OverviewScenarioRow } from "../../types/stats.types";
import { sortScenarioRows, toggleSortDirection } from "../sortScenarioRows";

const row = (
  title: string,
  plays: number,
  completion: number | null,
): OverviewScenarioRow => ({
  scenario_id: title,
  title,
  status: "published",
  plays,
  trend: null,
  completion_rate: completion,
  average_turns: null,
  average_rating: null,
});

const ROWS = [row("beta", 5, 0.2), row("Alpha", 9, null), row("gamma", 1, 0.9)];

describe("sortScenarioRows", () => {
  it("sorts numbers descending", () => {
    expect(sortScenarioRows(ROWS, "plays", "descending").map((r) => r.title)).toEqual([
      "Alpha",
      "beta",
      "gamma",
    ]);
  });

  it("sorts titles case-insensitively ascending", () => {
    expect(sortScenarioRows(ROWS, "title", "ascending").map((r) => r.title)).toEqual([
      "Alpha",
      "beta",
      "gamma",
    ]);
  });

  it("keeps empty values last in both directions", () => {
    expect(sortScenarioRows(ROWS, "completion_rate", "ascending").at(-1)?.title).toBe(
      "Alpha",
    );
    expect(sortScenarioRows(ROWS, "completion_rate", "descending").at(-1)?.title).toBe(
      "Alpha",
    );
  });

  it("toggles direction", () => {
    expect(toggleSortDirection("ascending")).toBe("descending");
    expect(toggleSortDirection("descending")).toBe("ascending");
  });
});
