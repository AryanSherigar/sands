import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import { server } from "@/test/msw/server";
import { LandingPage } from "../LandingPage";

const API_URL = "http://localhost:8000";
const SCENARIOS_URL = `${API_URL}/v1/scenarios`;
const PLAYTHROUGHS_URL = `${API_URL}/v1/users/me/playthroughs`;
const PROFILE_URL = `${API_URL}/v1/users/me`;

const buildScenario = (
  overrides: Partial<ScenarioSummaryResponse> = {},
): ScenarioSummaryResponse => ({
  scenario_id: "scenario-1",
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: "The Sunken Crown",
  logline: "A drowned kingdom wakes.",
  mode: "newbie",
  status: "published",
  genre_tags: ["Fantasy"],
  complexity_tier: "newbie",
  player_count_support: "solo",
  estimated_playtime: "2 hours",
  playtime_bucket: "long",
  is_mature: false,
  cover_image_url: "https://example.com/cover.png",
  content_tag: "Mature themes",
  play_count: 10,
  rating_avg: "4.5",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const listResponse = (items: ScenarioSummaryResponse[]) =>
  HttpResponse.json({ items, next_cursor: null, total_count: items.length });

function mockScenarios(items: ScenarioSummaryResponse[]): void {
  server.use(http.get(SCENARIOS_URL, () => listResponse(items)));
}

function signIn(): void {
  useAuthStore.setState({
    accessToken: "token",
    isAuthenticated: true,
    isLoading: false,
    user: { user_id: "user-1", display_name: "Eldrin", onboarding_completed: true },
  });
}

function renderLanding(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/setup/:id" element={<p>setup page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LandingPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
  });

  it("renders the featured scenario with its content tag", async () => {
    mockScenarios([buildScenario()]);
    renderLanding();

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Sunken Crown" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Mature themes")).toBeInTheDocument();
  });

  it("still renders a hero when no scenario has a cover image", async () => {
    mockScenarios([buildScenario({ cover_image_url: null })]);
    renderLanding();

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Sunken Crown" }),
    ).toBeInTheDocument();
  });

  it("opens the sign-in modal when a guest presses Play now", async () => {
    mockScenarios([buildScenario()]);
    renderLanding();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Play now" }));

    await waitFor(() =>
      expect(useSignInModalStore.getState().trigger).toBe("setup"),
    );
    expect(screen.queryByText("setup page")).not.toBeInTheDocument();
  });

  it("goes to setup when a signed-in user presses Play now", async () => {
    signIn();
    mockScenarios([buildScenario()]);
    server.use(
      http.get(PLAYTHROUGHS_URL, () => HttpResponse.json([])),
      http.get(PROFILE_URL, () => HttpResponse.json({})),
    );
    renderLanding();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Play now" }));

    expect(await screen.findByText("setup page")).toBeInTheDocument();
  });

  it("shows the Continue row first for a signed-in user with active runs", async () => {
    signIn();
    mockScenarios([buildScenario()]);
    server.use(
      http.get(PROFILE_URL, () => HttpResponse.json({})),
      http.get(PLAYTHROUGHS_URL, () =>
        HttpResponse.json([
          {
            playthrough_id: "run-1",
            scenario_id: "scenario-1",
            scenario_title: "The Sunken Crown",
            scenario_mode: "newbie",
            cover_image_url: null,
            turn_count: 12,
            status: "active",
            ended_outcome_tag: null,
            ended_outcome_title: null,
            ended_outcome_text: null,
            character_name: null,
            character_archetype: null,
            created_at: "2026-10-27T00:00:00Z",
            updated_at: "2026-10-27T00:00:00Z",
          },
        ]),
      ),
    );
    renderLanding();

    await screen.findByRole("heading", { name: "Continue your story" });
    const headings = screen.getAllByRole("heading", { level: 2 });
    expect(headings[0]).toHaveTextContent("Continue your story");
    expect(screen.getByText(/Turn 12/)).toBeInTheDocument();
  });

  it("has no Continue row for a guest", async () => {
    mockScenarios([buildScenario()]);
    renderLanding();

    await screen.findByRole("heading", { level: 1 });
    expect(
      screen.queryByRole("heading", { name: "Continue your story" }),
    ).not.toBeInTheDocument();
  });

  it("renders the Curated Canon featured worlds and Studio showcase band", async () => {
    mockScenarios([
      buildScenario(),
      buildScenario({
        scenario_id: "scenario-2",
        title: "The Drowned Library",
        rating_avg: "3.0",
      }),
    ]);
    renderLanding();

    expect(
      await screen.findByRole("heading", { name: "Featured worlds" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Curated canon")).toBeInTheDocument();
    expect(screen.getByText("The Drowned Library")).toBeInTheDocument();
    expect(screen.getByText("Authoring Architecture")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Two ways to build worlds" }),
    ).toBeInTheDocument();
  });

  it("hides the featured worlds section instead of padding it with placeholders", async () => {
    mockScenarios([buildScenario()]);
    renderLanding();

    await screen.findByRole("heading", { level: 1, name: "The Sunken Crown" });
    expect(
      screen.queryByRole("heading", { name: "Featured worlds" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Substratum 9")).not.toBeInTheDocument();
    expect(screen.queryByText("1,280")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Two ways to build worlds" }),
    ).toBeInTheDocument();
  });

  it("shows the empty state when nothing is published", async () => {
    mockScenarios([]);
    renderLanding();

    expect(
      await screen.findByRole("heading", { name: "No stories published yet" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "New Story" }),
    ).toBeInTheDocument();
  });
});
