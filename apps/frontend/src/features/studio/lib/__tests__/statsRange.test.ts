import { describe, expect, it } from "vitest";
import { parseStatsRange } from "../statsRange";

describe("parseStatsRange", () => {
  it("accepts known ranges", () => {
    expect(parseStatsRange("7d")).toBe("7d");
    expect(parseStatsRange("all")).toBe("all");
  });

  it("falls back to 30d for missing or garbage values", () => {
    expect(parseStatsRange(null)).toBe("30d");
    expect(parseStatsRange("365d")).toBe("30d");
    expect(parseStatsRange("<script>")).toBe("30d");
  });
});
