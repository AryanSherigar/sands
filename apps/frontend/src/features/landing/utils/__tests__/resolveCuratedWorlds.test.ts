import { describe, expect, it } from "vitest";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import { resolveCuratedWorlds } from "../resolveCuratedWorlds";

const buildScenario = (
  scenarioId: string,
  title: string,
): ScenarioSummaryResponse => ({
  scenario_id: scenarioId,
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title,
  logline: "A logline.",
  mode: "newbie",
  status: "published",
  genre_tags: ["Fantasy"],
  complexity_tier: "newbie",
  player_count_support: "solo",
  estimated_playtime: "2 hours",
  playtime_bucket: "long",
  is_mature: false,
  cover_image_url: null,
  content_tag: null,
  play_count: 10,
  rating_avg: "4.5",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
});

describe("resolveCuratedWorlds", () => {
  it("returns nothing when there are no real scenarios", () => {
    expect(resolveCuratedWorlds([])).toEqual([]);
    expect(resolveCuratedWorlds()).toEqual([]);
  });

  it("never pads the list with placeholder scenarios", () => {
    const items = [buildScenario("a", "Alpha"), buildScenario("b", "Beta")];

    const result = resolveCuratedWorlds(items);

    expect(result.map((item) => item.scenario_id)).toEqual(["a", "b"]);
  });

  it("leaves out the scenario shown in the hero", () => {
    const items = [buildScenario("a", "Alpha"), buildScenario("b", "Beta")];

    const result = resolveCuratedWorlds(items, "a");

    expect(result.map((item) => item.scenario_id)).toEqual(["b"]);
  });

  it("returns an empty list when the hero is the only scenario", () => {
    expect(resolveCuratedWorlds([buildScenario("a", "Alpha")], "a")).toEqual([]);
  });

  it("keeps at most four scenarios", () => {
    const items = ["a", "b", "c", "d", "e"].map((id) => buildScenario(id, id));

    expect(resolveCuratedWorlds(items)).toHaveLength(4);
  });
});
