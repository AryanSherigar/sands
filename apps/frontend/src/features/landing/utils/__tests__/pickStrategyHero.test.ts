import { describe, expect, it } from "vitest";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import { pickStrategyHero } from "../pickStrategyHero";

const buildScenario = (
  scenarioId: string,
  coverImageUrl: string | null,
): ScenarioSummaryResponse =>
  ({
    scenario_id: scenarioId,
    cover_image_url: coverImageUrl,
    mode: "strategy",
  }) as ScenarioSummaryResponse;

describe("pickStrategyHero", () => {
  it("returns null when there are no strategy scenarios", () => {
    expect(pickStrategyHero([])).toBeNull();
  });

  it("prefers a strategy scenario that has a cover", () => {
    const hero = pickStrategyHero([
      buildScenario("no-cover", null),
      buildScenario("with-cover", "https://cdn.test/cover.webp"),
    ]);
    expect(hero?.scenario_id).toBe("with-cover");
  });

  it("falls back to the first scenario when none has a cover", () => {
    const hero = pickStrategyHero([buildScenario("first", null)]);
    expect(hero?.scenario_id).toBe("first");
  });
});
