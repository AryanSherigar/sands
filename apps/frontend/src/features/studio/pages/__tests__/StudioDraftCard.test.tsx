import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { ToastHost } from "@/shared/components/feedback/ToastHost";
import { server } from "@/test/msw/server";
import { STUDIO_TABS_STORAGE_PREFIX } from "../../constants/studioTabs";
import type { MyScenarioSummary } from "../../types/scenario.types";
import { StudioPage } from "../StudioPage";

const LIST_URL = "http://localhost:8000/v1/scenarios";
const TWO_DAYS_AGO_ISO = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString();

const buildDraft = (overrides: Partial<MyScenarioSummary> = {}): MyScenarioSummary => ({
  scenario_id: "draft-1",
  creator_id: "user-1",
  title: "The Door Below",
  logline: "A keeper hears knocking from under the sea.",
  mode: "newbie",
  status: "draft",
  genre_tags: [],
  complexity_tier: "newbie",
  player_count_support: "solo",
  estimated_playtime: null,
  cover_image_url: null,
  content_tag: null,
  play_count: 0,
  rating_avg: "0.00",
  created_at: TWO_DAYS_AGO_ISO,
  updated_at: TWO_DAYS_AGO_ISO,
  review_count: 0,
  has_unpublished_changes: false,
  publish_error: null,
  content_edited_at: TWO_DAYS_AGO_ISO,
  ...overrides,
});

const serveList = (items: MyScenarioSummary[]): void => {
  server.use(
    http.get(LIST_URL, () =>
      HttpResponse.json({
        items,
        next_cursor: null,
        total_count: items.length,
        status_counts: { all: items.length, drafts: items.length, published: 0, archived: 0 },
      }),
    ),
  );
};

const renderList = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/studio"]}>
        <Routes>
          <Route path="/studio" element={<StudioPage />} />
          <Route path="/studio/:id/edit" element={<p>editor page</p>} />
        </Routes>
        <ToastHost />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("Studio list draft card", () => {
  beforeEach(() => localStorage.clear());

  it("shows the idea, progress, last edit and Continue", async () => {
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}draft-1`,
      JSON.stringify({ openTabIds: ["guide"], activeTabId: "guide", splitTabId: null, guideStep: 4 }),
    );
    serveList([buildDraft()]);
    renderList();

    const row = (await screen.findByText("The Door Below", { selector: "h2" })).closest("li") as HTMLElement;
    expect(within(row).getByText("A keeper hears knocking from under the sea.")).toBeInTheDocument();
    expect(within(row).getByText("Step 4 of 7 · Characters")).toBeInTheDocument();
    expect(within(row).getByRole("progressbar", { name: "Guide progress" })).toHaveAttribute("aria-valuenow", "4");
    expect(within(row).getByText("Edited 2d ago")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "Continue" })).toHaveAttribute("href", "/studio/draft-1/edit");
  });

  it("falls back to a step worked out from the idea when no step is remembered", async () => {
    serveList([buildDraft({ scenario_id: "a" }), buildDraft({ scenario_id: "b", title: "Blank", logline: null })]);
    renderList();

    expect(await screen.findByText("Step 2 of 7 · Premise")).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 7 · Idea")).toBeInTheDocument();
  });

  it("uses a typographic cover when the draft has no cover image", async () => {
    serveList([buildDraft()]);
    renderList();

    const row = (await screen.findByText("The Door Below", { selector: "h2" })).closest("li") as HTMLElement;
    expect(within(row).getByRole("img", { name: "The Door Below" })).toBeInTheDocument();
  });

  it("offers Duplicate, Archive and Delete draft in the menu", async () => {
    serveList([buildDraft()]);
    renderList();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "More actions for The Door Below" }));

    expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual([
      "Duplicate",
      "Archive",
      "Delete draft",
    ]);
  });

  it("archives the draft from the menu", async () => {
    const archived: Array<Record<string, unknown>> = [];
    serveList([buildDraft()]);
    server.use(
      http.patch(`${LIST_URL}/:id`, async ({ request }) => {
        archived.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(buildDraft({ status: "draft" }));
      }),
    );
    renderList();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "More actions for The Door Below" }));
    await user.click(screen.getByRole("menuitem", { name: "Archive" }));

    await waitFor(() => expect(archived).toEqual([{ status: "archived" }]));
  });

  it("leaves Advanced drafts as they were", async () => {
    serveList([buildDraft({ mode: "master", title: "Old Ledger" })]);
    renderList();

    expect(await screen.findByRole("link", { name: "Continue editing" })).toBeInTheDocument();
    expect(screen.queryByText(/Step \d of 7/)).toBeNull();
  });
});
