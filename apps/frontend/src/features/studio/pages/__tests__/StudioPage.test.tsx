import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastHost } from "@/shared/components/feedback/ToastHost";
import { server } from "@/test/msw/server";
import type {
  MyScenarioSummary,
  ScenarioStatusCounts,
} from "../../types/scenario.types";
import { StudioPage } from "../StudioPage";

const LIST_URL = "http://localhost:8000/v1/scenarios";
const NOW_ISO = new Date().toISOString();
const EMPTY_COUNTS: ScenarioStatusCounts = {
  all: 0,
  drafts: 0,
  published: 0,
  archived: 0,
};

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
  created_at: NOW_ISO,
  updated_at: NOW_ISO,
  review_count: 0,
  has_unpublished_changes: false,
  publish_error: null,
  content_edited_at: NOW_ISO,
  ...overrides,
});

const listResponse = (
  items: MyScenarioSummary[],
  overrides: Record<string, unknown> = {},
) => ({
  items,
  next_cursor: null,
  total_count: items.length,
  status_counts: { ...EMPTY_COUNTS, all: items.length },
  ...overrides,
});

const renderStudio = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/studio"]}>
        <Routes>
          <Route path="/studio" element={<StudioPage />} />
          <Route path="/studio/stats" element={<p>stats page</p>} />
          <Route path="/studio/:id/edit" element={<p>editor page</p>} />
        </Routes>
        <ToastHost />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const openRowMenu = async (title: string): Promise<void> => {
  await userEvent.click(
    await screen.findByRole("button", { name: `More actions for ${title}` }),
  );
};

describe("StudioPage", () => {
  it("opens creator stats from the header", async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json(listResponse([]))));
    renderStudio();

    await userEvent.click(screen.getByRole("button", { name: "Stats" }));

    expect(await screen.findByText("stats page")).toBeInTheDocument();
  });

  it("shows every status as text with the actions for that status", async () => {
    server.use(
      http.get(LIST_URL, () =>
        HttpResponse.json(
          listResponse([
            buildScenario({ scenario_id: "a", title: "Live", status: "published", play_count: 3420, review_count: 184, rating_avg: "4.90" }),
            buildScenario({ scenario_id: "b", title: "Live edited", status: "published", has_unpublished_changes: true }),
            buildScenario({ scenario_id: "c", title: "Unfinished", status: "draft" }),
            buildScenario({ scenario_id: "d", title: "Broken", status: "draft", publish_error: "content_tag is required" }),
            buildScenario({ scenario_id: "e", title: "Shelved", status: "archived" }),
            buildScenario({ scenario_id: "f", title: "In flight", status: "publishing" }),
          ]),
        ),
      ),
    );
    renderStudio();

    await screen.findByText("Live edited");
    const list = within(screen.getByRole("list"));
    expect(list.getByText("Published")).toBeInTheDocument();
    expect(list.getByText("Published — changes not yet published")).toBeInTheDocument();
    expect(list.getByText("Draft")).toBeInTheDocument();
    expect(list.getByText("Publish failed")).toBeInTheDocument();
    expect(list.getByText("Archived")).toBeInTheDocument();
    expect(list.getByText("Publishing…")).toBeInTheDocument();
    expect(screen.getByText("3,420")).toBeInTheDocument();
    expect(screen.getByText("(184)")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Playtest" })).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Continue editing" })).toBeInTheDocument();
    expect(screen.getByText("content_tag is required")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Fix and republish/ })).toHaveAttribute(
      "href",
      "/studio/d/edit#review",
    );
  });

  it("requests the active tab and the search text from the server", async () => {
    const requestedUrls: URL[] = [];
    server.use(
      http.get(LIST_URL, ({ request }) => {
        requestedUrls.push(new URL(request.url));
        return HttpResponse.json(listResponse([]));
      }),
    );
    renderStudio();

    await userEvent.click(await screen.findByRole("button", { name: /Drafts/ }));
    await userEvent.type(screen.getByLabelText("Filter worlds"), "noir");

    await waitFor(() => {
      const last = requestedUrls[requestedUrls.length - 1];
      expect(last.searchParams.get("tab")).toBe("drafts");
      expect(last.searchParams.get("q")).toBe("noir");
      expect(last.searchParams.get("sort")).toBe("edited");
    });
  });

  it("shows the empty states with the right action", async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json(listResponse([]))));
    renderStudio();

    expect(await screen.findByText("Create your first story")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New Story" })).toHaveLength(2);
  });

  it("names the empty tab and offers no action", async () => {
    server.use(
      http.get(LIST_URL, ({ request }) => {
        const isDraftsTab = new URL(request.url).searchParams.get("tab") === "drafts";
        return HttpResponse.json(
          listResponse([], {
            status_counts: { ...EMPTY_COUNTS, all: isDraftsTab ? 3 : 0, published: 3 },
          }),
        );
      }),
    );
    renderStudio();

    await userEvent.click(await screen.findByRole("button", { name: /Drafts/ }));

    expect(await screen.findByText("No drafts")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New Story" })).toHaveLength(1);
  });

  it("offers to clear a search that matches nothing", async () => {
    server.use(http.get(LIST_URL, () => HttpResponse.json(listResponse([]))));
    renderStudio();

    await userEvent.type(await screen.findByLabelText("Filter worlds"), "zzz");

    expect(await screen.findByText("No worlds match “zzz”")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getByLabelText("Filter worlds")).toHaveValue("");
  });

  it("requires the typed title before deleting a draft", async () => {
    const deletedIds: string[] = [];
    server.use(
      http.get(LIST_URL, () =>
        HttpResponse.json(listResponse([buildScenario({ scenario_id: "c", title: "Scrap" })])),
      ),
      http.delete(`${LIST_URL}/:id`, ({ params }) => {
        deletedIds.push(String(params.id));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderStudio();

    await openRowMenu("Scrap");
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    const confirmButton = within(dialog).getByRole("button", { name: "Delete scenario" });
    expect(confirmButton).toBeDisabled();
    await userEvent.type(within(dialog).getByRole("textbox"), "scrap");
    await userEvent.click(confirmButton);

    await waitFor(() => expect(deletedIds).toEqual(["c"]));
  });

  it("explains that deleting a published scenario archives it", async () => {
    server.use(
      http.get(LIST_URL, () =>
        HttpResponse.json(listResponse([buildScenario({ title: "Live", status: "published" })])),
      ),
    );
    renderStudio();

    await openRowMenu("Live");
    await userEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(await screen.findByText(/archives it and hides it from players/)).toBeInTheDocument();
  });

  it("does not offer Delete on archived rows", async () => {
    server.use(
      http.get(LIST_URL, () =>
        HttpResponse.json(listResponse([buildScenario({ title: "Shelved", status: "archived" })])),
      ),
    );
    renderStudio();

    await openRowMenu("Shelved");

    expect(screen.queryByRole("menuitem", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Duplicate" })).toBeInTheDocument();
  });

  it("toasts a copy with a link to it after Duplicate", async () => {
    server.use(
      http.get(LIST_URL, () =>
        HttpResponse.json(listResponse([buildScenario({ title: "Original" })])),
      ),
      http.post(`${LIST_URL}/:id/duplicate`, () =>
        HttpResponse.json({ scenario_id: "copy-1" }, { status: 201 }),
      ),
    );
    renderStudio();

    await openRowMenu("Original");
    await userEvent.click(screen.getByRole("menuitem", { name: "Duplicate" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));

    expect(await screen.findByText("editor page")).toBeInTheDocument();
  });
});

describe("StudioPage paging", () => {
  beforeEach(() => {
    class ImmediateIntersectionObserver {
      constructor(private readonly callback: IntersectionObserverCallback) {}
      observe(): void {
        this.callback(
          [{ isIntersecting: true } as IntersectionObserverEntry],
          this as unknown as IntersectionObserver,
        );
      }
      disconnect(): void {}
      unobserve(): void {}
      takeRecords(): IntersectionObserverEntry[] {
        return [];
      }
    }
    vi.stubGlobal("IntersectionObserver", ImmediateIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps loaded rows and offers Retry when the next page fails", async () => {
    let shouldFailSecondPage = true;
    server.use(
      http.get(LIST_URL, ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset");
        if (offset === "0") {
          return HttpResponse.json(
            listResponse([buildScenario({ scenario_id: "a", title: "First page" })], {
              next_cursor: "10",
              total_count: 11,
            }),
          );
        }
        if (shouldFailSecondPage) return new HttpResponse(null, { status: 500 });
        return HttpResponse.json(
          listResponse([buildScenario({ scenario_id: "b", title: "Second page" })], {
            total_count: 11,
          }),
        );
      }),
    );
    renderStudio();

    expect(await screen.findByText("Couldn't load more")).toBeInTheDocument();
    expect(screen.getByText("First page")).toBeInTheDocument();
    shouldFailSecondPage = false;
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Second page")).toBeInTheDocument();
  });
});
