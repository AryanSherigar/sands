import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { buildPlaytestSetupPath } from "@/shared/constants/navigation";
import { server } from "@/test/msw/server";
import type { ScenarioDetailResponse } from "../../types/scenario";
import { SetupPage } from "../SetupPage";

const API = "http://localhost:8000/v1";
const SCENARIO_ID = "scenario-1";

const DRAFT_SCENARIO: ScenarioDetailResponse = {
  scenario_id: SCENARIO_ID,
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: "The Grey Ledger",
  logline: "Three leaves torn from the vault.",
  mode: "master",
  status: "draft",
  genre_tags: [],
  complexity_tier: "intermediate",
  player_count_support: "solo",
  estimated_playtime: "45 min",
  playtime_bucket: "medium",
  is_mature: false,
  cover_image_url: null,
  content_tag: "teen",
  play_count: 0,
  rating_avg: "0.00",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  setup_schema: [
    {
      id: "field-1",
      key: "player_name",
      label: "Your name",
      type: "text",
      required: true,
      options: [],
    },
  ],
};

const renderSetupPage = (initialPath: string): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/setup/:id" element={<SetupPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("SetupPage in playtest mode", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: "token",
      isAuthenticated: true,
      isLoading: false,
      user: {
        user_id: "creator-1",
        display_name: "Ayla",
        onboarding_completed: true,
        show_mature: false,
      },
    });
    server.use(
      http.get(`${API}/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json(DRAFT_SCENARIO),
      ),
      http.get(`${API}/scenarios/${SCENARIO_ID}/reviews`, () =>
        HttpResponse.json({ items: [], total_count: 0 }),
      ),
    );
  });

  it("sends the filled setup values to the playtest endpoint", async () => {
    let playtestBody: unknown = null;
    let wasPlaythroughEndpointHit = false;
    server.use(
      http.post(
        `${API}/scenarios/${SCENARIO_ID}/playtest`,
        async ({ request }) => {
          playtestBody = await request.json();
          return HttpResponse.json(
            { playthrough_id: "run-1" },
            { status: 201 },
          );
        },
      ),
      http.post(`${API}/playthroughs`, () => {
        wasPlaythroughEndpointHit = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderSetupPage(buildPlaytestSetupPath(SCENARIO_ID));

    const user = userEvent.setup();
    await user.type(await screen.findByRole("textbox"), "Ash");
    await user.click(
      screen.getByRole("button", { name: /start adventure/i }),
    );

    await waitFor(() => {
      expect(playtestBody).toEqual({ setup_values: { player_name: "Ash" } });
    });
    expect(wasPlaythroughEndpointHit).toBe(false);
  });
});
