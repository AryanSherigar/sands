import { describe, expect, it } from "vitest";
import {
  formatBenchmarkValue,
  formatBucketLabel,
  formatCount,
  formatDecimal,
  formatPercent,
  formatTrend,
  summarizePlays,
  trendToneClass,
} from "../statsFormat";

describe("statsFormat", () => {
  it("formats empty values as a dash", () => {
    expect(formatCount(null)).toBe("—");
    expect(formatPercent(null)).toBe("—");
    expect(formatDecimal(null)).toBe("—");
  });

  it("formats numbers", () => {
    expect(formatCount(1234)).toBe("1,234");
    expect(formatPercent(0.456)).toBe("46%");
    expect(formatDecimal(4.25)).toBe("4.3");
  });

  it("formats trends with an arrow and the previous period", () => {
    expect(formatTrend({ percent_change: 0.123, is_new: false }, "30d")).toBe(
      "↑ 12% vs previous 30 days",
    );
    expect(formatTrend({ percent_change: -0.5, is_new: false }, "7d")).toBe(
      "↓ 50% vs previous 7 days",
    );
    expect(formatTrend({ percent_change: null, is_new: true }, "30d")).toBe("New");
    expect(formatTrend(null, "all")).toBeNull();
  });

  it("pairs trend colour with direction", () => {
    expect(trendToneClass({ percent_change: 0.1, is_new: false })).toBe("text-success");
    expect(trendToneClass({ percent_change: -0.1, is_new: false })).toBe("text-danger");
    expect(trendToneClass({ percent_change: null, is_new: true })).toBe(
      "text-content-muted",
    );
  });

  it("summarises plays with and without a trend", () => {
    expect(summarizePlays(12, null, "all")).toBe("12 plays in all time.");
    expect(summarizePlays(12, { percent_change: 0.2, is_new: false }, "30d")).toBe(
      "12 plays in the last 30 days (↑ 20% vs previous 30 days).",
    );
  });

  it("labels day and week buckets in UTC", () => {
    expect(formatBucketLabel("2026-10-27", "day")).toBe("Oct 27");
    expect(formatBucketLabel("2026-10-27", "week")).toBe("Week of Oct 27");
  });
});

describe("formatBenchmarkValue", () => {
  it("formats rates as percentages and counts as decimals", () => {
    expect(formatBenchmarkValue("completion_rate", 0.48)).toBe("48%");
    expect(formatBenchmarkValue("average_turns", 7)).toBe("7.0");
    expect(formatBenchmarkValue("average_rating", null)).toBe("—");
  });
});
