import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScenarioDetailResponse } from "../../../types/scenario";
import { ScenarioLoreSection } from "../ScenarioLoreSection";

const NARRATOR_PERSONA = "You narrate in the voice of a procedure manual.";

const buildScenario = (
  overrides: Partial<ScenarioDetailResponse> = {},
): ScenarioDetailResponse => ({
  scenario_id: "scenario-1",
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: "Night Desk, Floor 9",
  logline: "You were told it was just a night job.",
  mode: "master",
  status: "published",
  genre_tags: [],
  complexity_tier: "master",
  player_count_support: "solo",
  estimated_playtime: "45 min",
  playtime_bucket: "medium",
  is_mature: false,
  cover_image_url: null,
  content_tag: "teen",
  can_review: false,
  setup_schema: [],
  play_count: 0,
  rating_avg: "0.00",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

describe("ScenarioLoreSection", () => {
  it("shows the logline", () => {
    render(<ScenarioLoreSection scenario={buildScenario()} />);

    expect(
      screen.getByText("You were told it was just a night job."),
    ).toBeInTheDocument();
  });

  it("never shows the narrator tone to players", () => {
    render(
      <ScenarioLoreSection
        scenario={buildScenario({ narrator_persona: NARRATOR_PERSONA })}
      />,
    );

    expect(screen.queryByText("Narrator tone")).not.toBeInTheDocument();
    expect(screen.queryByText(NARRATOR_PERSONA)).not.toBeInTheDocument();
  });
});
