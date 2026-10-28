import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  configure,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import { useMatureRevealStore } from "../../stores/matureReveal.store";
import { server } from "@/test/msw/server";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import type {
  ScenarioDetailResponse,
  ScenarioEndingsResponse,
  ScenarioReviewResponse,
} from "../../types/scenario";
import { ScenarioFocusPage } from "../ScenarioFocusPage";

const API = "http://localhost:8000/v1";
const SCENARIO_ID = "scenario-1";
const ASYNC_UTIL_TIMEOUT_MS = 4000;

configure({ asyncUtilTimeout: ASYNC_UTIL_TIMEOUT_MS });

const buildScenario = (
  overrides: Partial<ScenarioDetailResponse> = {},
): ScenarioDetailResponse => ({
  scenario_id: SCENARIO_ID,
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: "The Grey Ledger",
  logline: "Three leaves torn from the vault.",
  mode: "master",
  status: "published",
  genre_tags: ["Noir / Detective", "Mystery"],
  complexity_tier: "intermediate",
  player_count_support: "solo",
  estimated_playtime: "45 min",
  playtime_bucket: "medium",
  is_mature: false,
  cover_image_url: null,
  content_tag: "teen",
  play_count: 3420,
  rating_avg: "4.90",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  can_review: false,
  setup_schema: [],
  ...overrides,
});

const buildReview = (
  overrides: Partial<ScenarioReviewResponse> = {},
): ScenarioReviewResponse => ({
  review_id: "review-1",
  scenario_id: SCENARIO_ID,
  user_id: "user-9",
  user_display_name: "maren_sol",
  rating: 5,
  comment: "Incredible consistency.",
  created_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const buildRun = (
  overrides: Partial<UserPlaythroughSummary> = {},
): UserPlaythroughSummary => ({
  playthrough_id: "run-1",
  scenario_id: SCENARIO_ID,
  scenario_title: "The Grey Ledger",
  scenario_mode: "master",
  cover_image_url: null,
  turn_count: 14,
  status: "active",
  ended_outcome_tag: null,
  ended_outcome_title: null,
  ended_outcome_text: null,
  character_name: null,
  character_archetype: null,
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

interface MockApiOptions {
  scenario?: ScenarioDetailResponse;
  reviews?: ScenarioReviewResponse[];
  ownReviewUserId?: string;
  runs?: UserPlaythroughSummary[];
  isReviewsFailing?: boolean;
  reviewRequests?: URL[];
  endings?: ScenarioEndingsResponse;
  isEndingsFailing?: boolean;
}

const STAR_LEVELS = [5, 4, 3, 2, 1];

function buildReviewsPage(
  allReviews: ScenarioReviewResponse[],
  url: URL,
  ownReviewUserId: string | undefined,
) {
  const limit = Number(url.searchParams.get("limit") ?? 20);
  const offset = Number(url.searchParams.get("offset") ?? 0);
  const total = allReviews.length;
  const ratingSum = allReviews.reduce((sum, review) => sum + review.rating, 0);
  return {
    items: allReviews.slice(offset, offset + limit),
    total_count: total,
    average_rating: total === 0 ? 0 : ratingSum / total,
    rating_counts: STAR_LEVELS.map((stars) => ({
      stars,
      count: allReviews.filter((review) => review.rating === stars).length,
    })),
    own_review:
      allReviews.find((review) => review.user_id === ownReviewUserId) ?? null,
  };
}

function mockApi({
  scenario = buildScenario(),
  reviews = [],
  ownReviewUserId,
  runs = [],
  isReviewsFailing = false,
  reviewRequests = [],
  endings = { total_count: 0, found: null },
  isEndingsFailing = false,
}: MockApiOptions = {}): void {
  server.use(
    http.get(`${API}/scenarios/${SCENARIO_ID}`, () => HttpResponse.json(scenario)),
    http.get(`${API}/scenarios/${SCENARIO_ID}/reviews`, ({ request }) => {
      const url = new URL(request.url);
      reviewRequests.push(url);
      if (isReviewsFailing) return new HttpResponse(null, { status: 500 });
      return HttpResponse.json(buildReviewsPage(reviews, url, ownReviewUserId));
    }),
    http.get(`${API}/scenarios/${SCENARIO_ID}/endings`, () =>
      isEndingsFailing
        ? new HttpResponse(null, { status: 500 })
        : HttpResponse.json(endings),
    ),
    http.get(`${API}/scenarios/${SCENARIO_ID}/playthroughs`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${API}/users/me/playthroughs`, () => HttpResponse.json(runs)),
  );
}

function setSignedIn(userId: string | null, showMature = false): void {
  useAuthStore.setState({
    accessToken: userId ? "token" : null,
    isAuthenticated: Boolean(userId),
    isLoading: false,
    user: userId
      ? {
          user_id: userId,
          display_name: "Eldrin",
          onboarding_completed: true,
          show_mature: showMature,
        }
      : null,
  });
}

const useAuthStoreShowMature = (): boolean | undefined =>
  useAuthStore.getState().user?.show_mature;

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/scenario/${SCENARIO_ID}`]}>
        <Routes>
          <Route path="/scenario/:id" element={<ScenarioFocusPage />} />
          <Route path="/discover" element={<p>Discover</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScenarioFocusPage", () => {
  beforeEach(() => {
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
    useMatureRevealStore.setState({ revealedScenarioIds: [] });
    setSignedIn(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the hero with title, creator, genres and a Play link that starts a new run", async () => {
    mockApi();
    renderPage();

    const title = await screen.findByRole("heading", {
      level: 1,
      name: "The Grey Ledger",
    });
    const hero = title.closest("section") as HTMLElement;
    expect(within(hero).getByRole("link", { name: /Ayla/ })).toHaveAttribute(
      "href",
      "/profile/creator-1",
    );
    expect(screen.getByText("Noir / Detective")).toBeInTheDocument();
    expect(screen.getByText("Mystery")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play" })).toHaveAttribute(
      "href",
      `/setup/${SCENARIO_ID}`,
    );
  });

  it("shows the not-found pattern with a way back to Explore stories", async () => {
    server.use(
      http.get(`${API}/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );
    renderPage();

    expect(await screen.findByText("Story not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Explore stories" })).toHaveAttribute(
      "href",
      "/discover",
    );
  });

  it("asks guests to sign in when they press Save", async () => {
    mockApi();
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(useSignInModalStore.getState().trigger).toBe("save"),
    );
  });

  it("hides the in-progress line for guests", async () => {
    mockApi({ runs: [buildRun()] });
    renderPage();

    await screen.findByRole("heading", { level: 1 });

    expect(screen.queryByText(/run in progress/)).not.toBeInTheDocument();
  });

  it("offers Continue for a single unfinished run of this story", async () => {
    setSignedIn("user-1");
    mockApi({ runs: [buildRun()] });
    renderPage();

    const continueLink = await screen.findByRole("link", { name: "Continue" });

    expect(continueLink).toHaveAttribute("href", "/play/run-1");
    expect(screen.getByText(/Turn 14/)).toBeInTheDocument();
  });

  it("links to the filtered campaigns list when several runs are in progress", async () => {
    setSignedIn("user-1");
    mockApi({ runs: [buildRun(), buildRun({ playthrough_id: "run-2" })] });
    renderPage();

    const viewLink = await screen.findByRole("link", { name: "View" });

    expect(screen.getByText(/2 runs in progress/)).toBeInTheDocument();
    expect(viewLink).toHaveAttribute(
      "href",
      `/profile?tab=campaigns&scenario=${SCENARIO_ID}`,
    );
  });

  it("labels Play as Playtest and shows the draft banner for the owner of a draft", async () => {
    setSignedIn("creator-1");
    mockApi({ scenario: buildScenario({ status: "draft" }) });
    renderPage();

    expect(
      await screen.findByText("Draft — only you can see this page"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Playtest" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Play" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Edit in Studio" })).not.toHaveLength(0);
  });

  it("only shows Edit in Studio to the creator", async () => {
    setSignedIn("user-1");
    mockApi();
    renderPage();

    await screen.findByRole("heading", { level: 1 });

    expect(screen.queryByRole("link", { name: "Edit in Studio" })).not.toBeInTheDocument();
  });

  it("says no setup is needed when the story has no setup fields", async () => {
    mockApi();
    renderPage();

    expect(
      await screen.findByText("No setup needed — jump straight in"),
    ).toBeInTheDocument();
  });

  it("lists what the player will choose from required setup fields", async () => {
    mockApi({
      scenario: buildScenario({
        setup_schema: [
          { id: "1", key: "name", label: "Name", type: "text", required: true, options: [] },
          { id: "2", key: "class", label: "Class", type: "text", required: true, options: [] },
        ],
      }),
    });
    renderPage();

    expect(await screen.findByText(/You'll choose:/)).toHaveTextContent(
      "You'll choose: Name, Class",
    );
  });

  it("orders chips creator tags, then mechanics, then the age chip, with explanations", async () => {
    mockApi({
      scenario: buildScenario({
        player_count_support: "both",
        content_tags: ["moral-ambiguity", "noir-atmosphere"],
      }),
    });
    renderPage();

    const heading = await screen.findByRole("heading", {
      name: "Mechanical & thematic profile",
    });
    const chips = within(heading.closest("section") as HTMLElement).getAllByRole("listitem");

    expect(chips.map((chip) => chip.textContent)).toEqual([
      expect.stringContaining("Moral ambiguity"),
      expect.stringContaining("Noir atmosphere"),
      expect.stringContaining("Dice & stat resolution"),
      expect.stringContaining("Multiplayer-capable"),
      expect.stringContaining("Teen"),
    ]);
    expect(chips[0]).toHaveAttribute("title");
  });

  it("shows signed-out viewers only how many endings the story has", async () => {
    mockApi({ endings: { total_count: 5, found: null } });
    renderPage();

    expect(await screen.findByText("This story has 5 endings")).toBeInTheDocument();
    expect(screen.queryByText(/Ending #/)).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows found endings in full and unfound ones as anonymous locked slots", async () => {
    setSignedIn("user-1");
    mockApi({
      endings: {
        total_count: 3,
        found: [
          {
            ending_id: "end-1",
            title: "Ashen Dawn",
            text: "You burned the ledger.",
            outcome_tag: "win",
            turn_reached: 24,
            found_at: "2026-10-27T10:00:00Z",
          },
        ],
      },
    });
    renderPage();

    expect(await screen.findByText("Endings found (1 of 3)")).toBeInTheDocument();
    expect(screen.getByText("33% complete")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ashen Dawn" })).toBeInTheDocument();
    expect(screen.getByText("You burned the ledger.")).toBeInTheDocument();
    expect(screen.getByText(/Turn 24 · Victory/)).toBeInTheDocument();
    expect(screen.getByText("Ending #2")).toBeInTheDocument();
    expect(screen.getByText("Ending #3")).toBeInTheDocument();
    expect(screen.getAllByText("Not found yet")).toHaveLength(2);
  });

  it("hides the endings section when the story has no author endings", async () => {
    setSignedIn("user-1");
    mockApi({ endings: { total_count: 0, found: [] } });
    renderPage();

    await screen.findByRole("heading", { level: 1 });

    expect(screen.queryByText(/Endings/)).not.toBeInTheDocument();
  });

  it("degrades the endings section to an inline error with Retry", async () => {
    mockApi({ isEndingsFailing: true });
    renderPage();

    expect(await screen.findByText("Couldn't load endings")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play" })).toBeInTheDocument();
  });

  it("explains the review requirement to signed-in players who haven't played 10 turns", async () => {
    setSignedIn("user-1");
    mockApi();
    renderPage();

    expect(
      await screen.findByText("Play at least 10 turns to review"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Post review" })).not.toBeInTheDocument();
  });

  it("opens the sign-in modal for guests who try to write a review", async () => {
    mockApi();
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Write a review" }));

    await waitFor(() =>
      expect(useSignInModalStore.getState().trigger).toBe("review"),
    );
  });

  it("pins the viewer's own review first, once, and makes it editable", async () => {
    setSignedIn("user-1");
    mockApi({
      ownReviewUserId: "user-1",
      reviews: [
        buildReview(),
        buildReview({
          review_id: "review-2",
          user_id: "user-1",
          user_display_name: "Eldrin",
          comment: "Mine.",
        }),
      ],
    });
    renderPage();

    expect(await screen.findByRole("button", { name: "Update review" })).toBeInTheDocument();
    const names = screen
      .getAllByRole("listitem")
      .map((item) => item.textContent ?? "")
      .filter((text) => /maren_sol|Eldrin/.test(text));
    expect(names).toHaveLength(2);
    expect(names[0]).toContain("Eldrin");
  });

  it("builds the histogram from all reviews and shows the rating as text", async () => {
    mockApi({
      reviews: [
        buildReview({ review_id: "a", rating: 5 }),
        buildReview({ review_id: "b", rating: 5 }),
        buildReview({ review_id: "c", rating: 1 }),
        buildReview({ review_id: "d", rating: 5 }),
      ],
    });
    renderPage();

    expect(
      await screen.findByText("Rated 4.0 out of 5 from 4 reviews"),
    ).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
  });

  it("loads the next page when Show more is pressed and hides it at the end", async () => {
    const reviewRequests: URL[] = [];
    const reviews = Array.from({ length: 12 }, (_, index) =>
      buildReview({
        review_id: `review-${index}`,
        user_id: `user-${index}`,
        user_display_name: `reviewer_${index}`,
      }),
    );
    mockApi({ reviews, reviewRequests });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Show more" }));

    expect(await screen.findByText("reviewer_11")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
    expect(reviewRequests.map((url) => url.searchParams.get("offset"))).toEqual([
      "0",
      "10",
    ]);
    expect(reviewRequests[0].searchParams.get("limit")).toBe("10");
  });

  it("shows the author dossier with bio and other-scenario count for anyone, owner included", async () => {
    setSignedIn("creator-1");
    mockApi({
      scenario: buildScenario({
        creator_bio: "Architecting noir.",
        creator_other_scenarios_count: 3,
      }),
    });
    renderPage();

    const dossier = await screen.findByRole("region", { name: "About the author" });

    expect(within(dossier).getByText("Architecting noir.")).toBeInTheDocument();
    expect(
      within(dossier).getByRole("link", { name: /View 3 other scenarios by Ayla/ }),
    ).toHaveAttribute("href", "/profile/creator-1");
  });

  it("omits the bio and the other-scenarios link when there is nothing to show", async () => {
    mockApi({
      scenario: buildScenario({ creator_bio: null, creator_other_scenarios_count: 0 }),
    });
    renderPage();

    const dossier = await screen.findByRole("region", { name: "About the author" });

    expect(within(dossier).queryByText(/other scenario/)).not.toBeInTheDocument();
    expect(within(dossier).getAllByRole("link")).toHaveLength(1);
  });

  it("shows map and minigame chips when the story has them", async () => {
    mockApi({ scenario: buildScenario({ has_maps: true, has_minigames: true }) });
    renderPage();

    expect(await screen.findByText("Map exploration")).toBeInTheDocument();
    expect(screen.getByText("Minigames")).toBeInTheDocument();
  });

  it("degrades the reviews section to an inline error with Retry while Play still works", async () => {
    mockApi({ isReviewsFailing: true });
    renderPage();

    expect(await screen.findByText("Couldn't load reviews")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play" })).toBeInTheDocument();
  });

  describe("mature gate", () => {
    const matureScenario = (overrides: Partial<ScenarioDetailResponse> = {}) =>
      buildScenario({ is_mature: true, content_tag: "mature", ...overrides });

    it("covers the body for a viewer who has not opted in, while the title stays visible", async () => {
      mockApi({ scenario: matureScenario() });
      renderPage();

      expect(
        await screen.findByRole("heading", { name: "This story is marked mature" }),
      ).toBeInTheDocument();
      expect(screen.getByRole("heading", { level: 1, name: "The Grey Ledger" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "About" })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Reviews" })).not.toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Change in Settings" })).toHaveAttribute(
        "href",
        "/settings",
      );
    });

    it("reveals the body on Show anyway without saving any preference", async () => {
      const saves: unknown[] = [];
      server.use(
        http.patch(`${API}/users/me`, async ({ request }) => {
          saves.push(await request.json());
          return HttpResponse.json({ show_mature: true });
        }),
      );
      setSignedIn("user-1", false);
      mockApi({ scenario: matureScenario() });
      renderPage();

      await userEvent.click(await screen.findByRole("button", { name: "Show anyway" }));

      expect(await screen.findByRole("heading", { name: "About" })).toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "This story is marked mature" }),
      ).not.toBeInTheDocument();
      expect(saves).toEqual([]);
      expect(useAuthStoreShowMature()).toBe(false);
    });

    it("does not gate a viewer who saved the opt-in", async () => {
      setSignedIn("user-1", true);
      mockApi({ scenario: matureScenario() });
      renderPage();

      expect(await screen.findByRole("heading", { name: "About" })).toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "This story is marked mature" }),
      ).not.toBeInTheDocument();
    });

    it("never gates the creator on their own story", async () => {
      setSignedIn("creator-1", false);
      mockApi({ scenario: matureScenario() });
      renderPage();

      expect(await screen.findByRole("heading", { name: "About" })).toBeInTheDocument();
    });

    it("does not gate stories that are not mature", async () => {
      mockApi();
      renderPage();

      expect(await screen.findByRole("heading", { name: "About" })).toBeInTheDocument();
    });

    it("hides the sticky Play bar while the story is gated", async () => {
      let notifyVisibility: (isIntersecting: boolean) => void = () => undefined;
      vi.stubGlobal(
        "IntersectionObserver",
        class {
          constructor(callback: IntersectionObserverCallback) {
            notifyVisibility = (isIntersecting) =>
              callback(
                [{ isIntersecting } as IntersectionObserverEntry],
                this as unknown as IntersectionObserver,
              );
          }
          observe(): void {}
          disconnect(): void {}
        },
      );
      mockApi({ scenario: matureScenario() });
      renderPage();
      await screen.findByRole("heading", { name: "This story is marked mature" });

      act(() => notifyVisibility(false));

      expect(screen.getAllByRole("link", { name: "Play" })).toHaveLength(1);
    });
  });

  it("shows the sticky Play bar only after the hero Play scrolls out of view", async () => {
    let notifyVisibility: (isIntersecting: boolean) => void = () => undefined;
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        constructor(callback: IntersectionObserverCallback) {
          notifyVisibility = (isIntersecting) =>
            callback(
              [{ isIntersecting } as IntersectionObserverEntry],
              this as unknown as IntersectionObserver,
            );
        }
        observe(): void {}
        disconnect(): void {}
      },
    );
    mockApi();
    renderPage();
    await screen.findByRole("heading", { level: 1 });

    expect(screen.getAllByRole("link", { name: "Play" })).toHaveLength(1);

    act(() => notifyVisibility(false));

    expect(screen.getAllByRole("link", { name: "Play" }).length).toBeGreaterThan(1);
  });
});
