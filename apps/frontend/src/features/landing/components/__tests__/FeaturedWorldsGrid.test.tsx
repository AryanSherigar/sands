import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import { FeaturedWorldsGrid } from "../FeaturedWorldsGrid";

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

const SCENARIOS = [
  buildScenario("scenario-1", "The Sunken Crown"),
  buildScenario("scenario-2", "The Drowned Library"),
  buildScenario("scenario-3", "Salt and Lantern"),
  buildScenario("scenario-4", "The Tin Orchard"),
];

describe("FeaturedWorldsGrid", () => {
  it("renders the curated canon section and 4 scenario cards", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <FeaturedWorldsGrid scenarios={SCENARIOS} totalCount={42} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Curated canon")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Featured worlds" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Browse all (42)")).toBeInTheDocument();
    expect(screen.getByText("The Sunken Crown")).toBeInTheDocument();
    expect(screen.getByText("The Drowned Library")).toBeInTheDocument();
    expect(screen.getByText("Salt and Lantern")).toBeInTheDocument();
    expect(screen.getByText("The Tin Orchard")).toBeInTheDocument();
  });
});
