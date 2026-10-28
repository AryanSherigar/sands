import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { MatureAttestationDialog } from "@/shared/components/MatureAttestationDialog/MatureAttestationDialog";
import { useMatureAttestationStore } from "@/shared/stores/matureAttestation.store";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import { server } from "@/test/msw/server";
import { DISCOVER_VIEW_STORAGE_KEY } from "../../constants/discover.constants";
import { useDiscoverViewStore } from "../../stores/discoverView.store";
import { DiscoverPage } from "../DiscoverPage";

const SCENARIOS_URL = "http://localhost:8000/v1/scenarios";

const buildScenario = (
  index: number,
  overrides: Partial<ScenarioSummaryResponse> = {},
): ScenarioSummaryResponse => ({
  scenario_id: `scenario-${index}`,
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: `Story ${index}`,
  logline: "A tale.",
  mode: "newbie",
  status: "published",
  genre_tags: ["Horror"],
  complexity_tier: "newbie",
  player_count_support: "solo",
  estimated_playtime: "1 hour",
  playtime_bucket: "short",
  is_mature: false,
  cover_image_url: null,
  content_tag: null,
  play_count: 5,
  rating_avg: "4.5",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

function respondWith(items: ScenarioSummaryResponse[], nextCursor: string | null = null) {
  return HttpResponse.json({
    items,
    next_cursor: nextCursor,
    total_count: items.length,
  });
}

function setSignedIn(isAuthenticated: boolean, showMature = false): void {
  useAuthStore.setState({
    accessToken: isAuthenticated ? "token" : null,
    isAuthenticated,
    isLoading: false,
    user: isAuthenticated
      ? {
          user_id: "user-1",
          display_name: "Eldrin",
          onboarding_completed: true,
          show_mature: showMature,
        }
      : null,
  });
}

function renderDiscover(initialPath = "/discover"): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MatureAttestationDialog />
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/scenario/:id" element={<p>Scenario page</p>} />
          <Route path="/setup/:id" element={<p>Setup page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DiscoverPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useDiscoverViewStore.setState({ view: "list" });
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
    useMatureAttestationStore.setState({ isOpen: false, resolvePending: null });
    setSignedIn(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists stories with a count and a list view by default", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1), buildScenario(2)])));
    renderDiscover();

    expect(await screen.findByRole("link", { name: "Story 1" })).toBeInTheDocument();
    expect(screen.getByText("2 stories")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "List" })).toBeChecked();
  });

  it("remembers the chosen view for this viewer", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await userEvent.click(await screen.findByRole("radio", { name: "Grid" }));

    expect(window.localStorage.getItem(DISCOVER_VIEW_STORAGE_KEY)).toBe("grid");
  });

  it("sends URL filters to the API and shows them as removable chips", async () => {
    const requests: URL[] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        requests.push(new URL(request.url));
        return respondWith([buildScenario(1)]);
      }),
    );
    renderDiscover("/discover?q=dragon&genre=Horror&type=advanced");

    await screen.findByRole("link", { name: "Story 1" });

    const params = requests[0].searchParams;
    expect(params.get("q")).toBe("dragon");
    expect(params.getAll("genre_tags")).toEqual(["Horror"]);
    expect(params.get("mode")).toBe("master");
    expect(screen.getByText("Results for 'dragon' · 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove filter: Advanced" })).toBeInTheDocument();
  });

  it("never shows the old tier names in the UI", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();
    await screen.findByRole("link", { name: "Story 1" });

    expect(screen.queryByText(/newbie|intermediate|master/i)).not.toBeInTheDocument();
  });

  it("asks the API for 10 stories at a time, most popular first", async () => {
    const requests: URL[] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        requests.push(new URL(request.url));
        return respondWith([buildScenario(1)]);
      }),
    );
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });

    expect(requests[0].searchParams.get("limit")).toBe("10");
    expect(requests[0].searchParams.get("sort")).toBe("play_count");
    expect(
      screen.getByRole("button", { name: /sort:\s*popular/i }),
    ).toBeInTheDocument();
  });

  it("has no Complexity or Length filters and ignores their old URL params", async () => {
    const requests: URL[] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        requests.push(new URL(request.url));
        return respondWith([buildScenario(1)]);
      }),
    );
    renderDiscover("/discover?complexity=deep&length=short");

    await screen.findByRole("link", { name: "Story 1" });

    expect(requests[0].searchParams.has("complexity_tier")).toBe(false);
    expect(requests[0].searchParams.has("playtime_bucket")).toBe(false);
    expect(screen.queryByText("Complexity")).not.toBeInTheDocument();
    expect(screen.queryByText("Length")).not.toBeInTheDocument();
  });

  it("filters by type from the segmented control", async () => {
    const modes: (string | null)[] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        modes.push(new URL(request.url).searchParams.get("mode"));
        return respondWith([buildScenario(1)]);
      }),
    );
    renderDiscover();
    await screen.findByRole("link", { name: "Story 1" });

    await userEvent.click(screen.getAllByRole("radio", { name: "Advanced" })[0]);

    await waitFor(() => expect(modes).toContain("master"));
    expect(screen.getByRole("button", { name: "Remove filter: Advanced" })).toBeInTheDocument();
  });

  it("shows how many stories are loaded and keeps Play and Save visible", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1), buildScenario(2)])));
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });

    expect(screen.getByText("Showing 2 of 2 scenarios")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Play/ })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Save: Story 2" })).toBeVisible();
  });

  it("navigates to scenario page when clicking scenario card in list view", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });
    const card = screen.getByText("A tale.").closest("article");
    expect(card).not.toBeNull();
    await userEvent.click(card as HTMLElement);

    expect(await screen.findByText("Scenario page")).toBeInTheDocument();
  });

  it("navigates to scenario page when clicking scenario card in grid view", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });
    await userEvent.click(screen.getByRole("radio", { name: "Grid" }));

    const card = screen.getByText("★ 4.5").closest("article");
    expect(card).not.toBeNull();
    await userEvent.click(card as HTMLElement);

    expect(await screen.findByText("Scenario page")).toBeInTheDocument();
  });

  it("navigates to setup screen when clicking play button without opening scenario page", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });
    const playButton = screen.getByRole("link", { name: /Play/ });
    await userEvent.click(playButton);

    expect(await screen.findByText("Setup page")).toBeInTheDocument();
    expect(screen.queryByText("Scenario page")).not.toBeInTheDocument();
  });

  it("saves scenario when clicking save button without navigating", async () => {
    server.use(
      http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])),
      http.post(`${SCENARIOS_URL}/scenario-1/bookmark`, () =>
        HttpResponse.json({ is_bookmarked: true }),
      ),
    );
    renderDiscover();

    const saveButton = await screen.findByRole("button", { name: "Save: Story 1" });
    await userEvent.click(saveButton);

    expect(await screen.findByRole("button", { name: "Saved: Story 1" })).toBeInTheDocument();
    expect(screen.queryByText("Scenario page")).not.toBeInTheDocument();
    expect(screen.queryByText("Setup page")).not.toBeInTheDocument();
  });

  it("opens a random loaded scenario from Surprise me", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0.99);
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1), buildScenario(2)])));
    renderDiscover();
    await screen.findByRole("link", { name: "Story 1" });

    await userEvent.click(screen.getByRole("button", { name: "Surprise me" }));

    expect(await screen.findByText("Scenario page")).toBeInTheDocument();
  });

  it("disables Surprise me when there is nothing to pick", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([])));
    renderDiscover();

    await screen.findByText("No stories yet");

    expect(screen.getByRole("button", { name: "Surprise me" })).toBeDisabled();
  });

  it("offers Clear filters when filters match nothing", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([])));
    renderDiscover("/discover?genre=Horror");

    expect(await screen.findByText("No stories match these filters")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear filters" })).toBeInTheDocument();
  });

  it("shows a specific empty state for Saved without an action", async () => {
    server.use(http.get(SCENARIOS_URL, () => respondWith([])));
    renderDiscover("/discover?saved=true");

    expect(
      await screen.findByText("Nothing saved yet — use Save on any story"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();
  });

  it("shows a removed story in Played without links to its page or setup", async () => {
    setSignedIn(true);
    server.use(
      http.get(SCENARIOS_URL, () =>
        respondWith([buildScenario(1, { title: "Gone Tale", status: "archived" })]),
      ),
    );
    renderDiscover("/discover?played=true");

    const card = (await screen.findByText("Gone Tale")).closest("article");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("Removed by creator")).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Surprise me/ })).toBeDisabled();
  });

  it("shows an inline error with Retry while filters stay usable", async () => {
    server.use(http.get(SCENARIOS_URL, () => new HttpResponse(null, { status: 500 })));
    renderDiscover();

    expect(await screen.findByRole("alert")).toHaveTextContent("couldn't load stories");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Horror/ })).toBeEnabled();
  });

  it("asks guests to sign in instead of showing personal lists", async () => {
    setSignedIn(false);
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await screen.findByRole("link", { name: "Story 1" });

    expect(screen.getByText(/Sign in to see stories you've played and saved/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Played" })).not.toBeInTheDocument();
  });

  it("opens the sign-in modal when a guest presses Save", async () => {
    setSignedIn(false);
    server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
    renderDiscover();

    await userEvent.click(await screen.findByRole("button", { name: "Save: Story 1" }));

    await waitFor(() => expect(useSignInModalStore.getState().trigger).toBe("save"));
  });

  it("toggles Save optimistically for a signed-in viewer", async () => {
    server.use(
      http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])),
      http.post(`${SCENARIOS_URL}/scenario-1/bookmark`, () =>
        HttpResponse.json({ is_bookmarked: true }),
      ),
    );
    renderDiscover();

    await userEvent.click(await screen.findByRole("button", { name: "Save: Story 1" }));

    expect(await screen.findByRole("button", { name: "Saved: Story 1" })).toBeInTheDocument();
  });

  it("loads the next page from the Load more button", async () => {
    const offsets: string[] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset") ?? "0";
        offsets.push(offset);
        return offset === "0"
          ? respondWith([buildScenario(1)], "10")
          : respondWith([buildScenario(2)]);
      }),
    );
    renderDiscover();

    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));

    expect(await screen.findByRole("link", { name: "Story 2" })).toBeInTheDocument();
    expect(offsets).toEqual(["0", "10"]);
  });

  it("applies sheet filters only when Show results is pressed", async () => {
    const genreRequests: string[][] = [];
    server.use(
      http.get(SCENARIOS_URL, ({ request }) => {
        genreRequests.push(new URL(request.url).searchParams.getAll("genre_tags"));
        return respondWith([buildScenario(1)]);
      }),
    );
    renderDiscover();
    await userEvent.click(await screen.findByRole("button", { name: "Filters" }));

    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    await userEvent.click(within(dialog).getByRole("checkbox", { name: /Horror/ }));
    expect(screen.queryByRole("button", { name: /Remove filter: Horror/ })).not.toBeInTheDocument();

    await userEvent.click(await within(dialog).findByRole("button", { name: /Show 1 results/ }));

    expect(await screen.findByRole("button", { name: "Remove filter: Horror" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  describe("mature stories and the saved preference", () => {
    const USERS_ME_URL = "http://localhost:8000/v1/users/me";

    const trackScenarioRequests = (requests: URL[]): void => {
      server.use(
        http.get(SCENARIOS_URL, ({ request }) => {
          requests.push(new URL(request.url));
          return respondWith([buildScenario(1)]);
        }),
      );
    };

    const trackPreferenceSaves = (saves: unknown[]): void => {
      server.use(
        http.patch(USERS_ME_URL, async ({ request }) => {
          const body = (await request.json()) as { show_mature: boolean };
          saves.push(body);
          return HttpResponse.json({ show_mature: body.show_mature });
        }),
      );
    };

    const getMatureSwitch = (): HTMLElement =>
      screen.getByRole("switch", { name: "Show mature stories" });

    it("starts with mature stories included when the viewer saved that preference", async () => {
      setSignedIn(true, true);
      const requests: URL[] = [];
      trackScenarioRequests(requests);
      renderDiscover();

      await screen.findByRole("link", { name: "Story 1" });

      expect(getMatureSwitch()).toBeChecked();
      expect(requests[0].searchParams.get("include_mature")).toBe("true");
    });

    it("keeps them out by default", async () => {
      const requests: URL[] = [];
      trackScenarioRequests(requests);
      renderDiscover();

      await screen.findByRole("link", { name: "Story 1" });

      expect(getMatureSwitch()).not.toBeChecked();
      expect(requests[0].searchParams.get("include_mature")).toBe("false");
    });

    it("asks a signed-in viewer to confirm they are 18+ before including them, then saves it", async () => {
      const requests: URL[] = [];
      const saves: unknown[] = [];
      trackScenarioRequests(requests);
      trackPreferenceSaves(saves);
      renderDiscover();
      await screen.findByRole("link", { name: "Story 1" });

      await userEvent.click(getMatureSwitch());
      expect(saves).toEqual([]);
      expect(getMatureSwitch()).not.toBeChecked();

      await userEvent.click(
        await screen.findByRole("checkbox", { name: "I confirm I am 18 or older" }),
      );
      await userEvent.click(screen.getByRole("button", { name: "Show mature content" }));

      await waitFor(() => expect(getMatureSwitch()).toBeChecked());
      expect(saves).toEqual([{ show_mature: true }]);
      await waitFor(() =>
        expect(requests.at(-1)?.searchParams.get("include_mature")).toBe("true"),
      );
    });

    it("leaves the filter off when the confirmation is cancelled", async () => {
      const saves: unknown[] = [];
      server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
      trackPreferenceSaves(saves);
      renderDiscover();
      await screen.findByRole("link", { name: "Story 1" });

      await userEvent.click(getMatureSwitch());
      await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));

      await waitFor(() =>
        expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument(),
      );
      expect(getMatureSwitch()).not.toBeChecked();
      expect(saves).toEqual([]);
    });

    it("saves the change when a viewer turns the saved preference off", async () => {
      setSignedIn(true, true);
      const saves: unknown[] = [];
      server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
      trackPreferenceSaves(saves);
      renderDiscover();
      await screen.findByRole("link", { name: "Story 1" });

      await userEvent.click(getMatureSwitch());

      await waitFor(() => expect(getMatureSwitch()).not.toBeChecked());
      expect(saves).toEqual([{ show_mature: false }]);
    });

    it("lets a guest use the filter without asking or saving anything", async () => {
      setSignedIn(false);
      const saves: unknown[] = [];
      server.use(http.get(SCENARIOS_URL, () => respondWith([buildScenario(1)])));
      trackPreferenceSaves(saves);
      renderDiscover();
      await screen.findByRole("link", { name: "Story 1" });

      await userEvent.click(getMatureSwitch());

      expect(getMatureSwitch()).toBeChecked();
      expect(saves).toEqual([]);
      expect(screen.queryByRole("checkbox", { name: /18 or older/ })).not.toBeInTheDocument();
    });
  });
});
