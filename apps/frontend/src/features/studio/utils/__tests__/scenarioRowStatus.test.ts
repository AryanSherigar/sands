import { describe, expect, it } from "vitest";
import type { MyScenarioSummary } from "../../types/scenario.types";
import {
  getDeleteOutcome,
  getDisplayStatus,
  isTitleConfirmed,
} from "../scenarioRowStatus";

const buildScenario = (
  overrides: Partial<MyScenarioSummary>,
): MyScenarioSummary => ({
  scenario_id: "scenario-1",
  creator_id: "user-1",
  title: "The Grey Ledger",
  logline: null,
  mode: "master",
  status: "draft",
  genre_tags: [],
  complexity_tier: "master",
  player_count_support: "solo",
  estimated_playtime: null,
  cover_image_url: null,
  content_tag: null,
  play_count: 0,
  rating_avg: "0.00",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  review_count: 0,
  has_unpublished_changes: false,
  publish_error: null,
  content_edited_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

describe("getDisplayStatus", () => {
  it("shows a first-time failed publish as publish_failed", () => {
    const scenario = buildScenario({ status: "draft", publish_error: "boom" });

    expect(getDisplayStatus(scenario)).toBe("publish_failed");
  });

  it("flags a published scenario with newer edits", () => {
    const scenario = buildScenario({
      status: "published",
      has_unpublished_changes: true,
    });

    expect(getDisplayStatus(scenario)).toBe("published_changes");
  });

  it("passes through plain statuses", () => {
    expect(getDisplayStatus(buildScenario({ status: "archived" }))).toBe(
      "archived",
    );
  });
});

describe("getDeleteOutcome", () => {
  it("archives anything that was ever published", () => {
    expect(getDeleteOutcome(buildScenario({ status: "published" }))).toBe(
      "archived",
    );
    expect(getDeleteOutcome(buildScenario({ status: "publish_failed" }))).toBe(
      "archived",
    );
  });

  it("deletes drafts, including first-time failed publishes", () => {
    const failedDraft = buildScenario({ status: "draft", publish_error: "x" });

    expect(getDeleteOutcome(failedDraft)).toBe("deleted");
  });
});

describe("isTitleConfirmed", () => {
  it("ignores case and surrounding spaces", () => {
    expect(isTitleConfirmed("  the grey LEDGER ", "The Grey Ledger", "Untitled")).toBe(true);
  });

  it("expects the fallback word for an untitled scenario", () => {
    expect(isTitleConfirmed("untitled", "  ", "Untitled")).toBe(true);
    expect(isTitleConfirmed("", "  ", "Untitled")).toBe(false);
  });
});
