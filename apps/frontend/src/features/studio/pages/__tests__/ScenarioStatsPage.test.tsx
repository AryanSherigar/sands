import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { buildScenarioStats } from "../../test/statsFixtures";
import type { ScenarioStatsResponse } from "../../types/stats.types";
import { ScenarioStatsPage } from "../ScenarioStatsPage";

const STATS_URL = "http://localhost:8000/v1/scenarios/scn-1/stats";

function mockStats(body: ScenarioStatsResponse): { ranges: string[] } {
  const ranges: string[] = [];
  server.use(
    http.get(STATS_URL, ({ request }) => {
      ranges.push(new URL(request.url).searchParams.get("range") ?? "");
      return HttpResponse.json(body);
    }),
  );
  return { ranges };
}

function renderPage(path = "/studio/scn-1/stats"): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/studio/:id/stats" element={<ScenarioStatsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScenarioStatsPage", () => {
  it("renders every Slice 1 section with charts and summaries", async () => {
    mockStats(buildScenarioStats());
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "The Hollow Cairn" }),
    ).toBeInTheDocument();
    for (const heading of [
      "Plays & players",
      "Outcomes",
      "Engagement",
      "Funnel & retention",
      "Ratings & reviews",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }
    expect(screen.getByText("Plays over time")).toBeInTheDocument();
    expect(screen.getByText("Player funnel")).toBeInTheDocument();
    expect(screen.getByText("Loved the cairn.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View public page" })).toHaveAttribute(
      "href",
      "/scenario/scn-1",
    );
  });

  it("shows counts only and a share prompt under the sample threshold", async () => {
    mockStats(buildScenarioStats({ is_sample_sufficient: false }));
    renderPage();

    expect(await screen.findByText("Stats appear after 5 plays.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share your story" })).toBeInTheDocument();
    expect(screen.queryByText("Plays over time")).not.toBeInTheDocument();
    expect(screen.queryByText("Player funnel")).not.toBeInTheDocument();
    expect(screen.queryByText("Rating distribution")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Location heatmap" }),
    ).not.toBeInTheDocument();
  });

  it("omits outcomes for a newbie scenario", async () => {
    const stats = buildScenarioStats({ outcomes: null });
    mockStats({ ...stats, scenario: { ...stats.scenario, mode: "newbie" } });
    renderPage();

    await screen.findByRole("heading", { name: "Plays & players" });
    expect(screen.queryByRole("heading", { name: "Outcomes" })).not.toBeInTheDocument();
  });

  it("asks the creator to publish a draft", async () => {
    const stats = buildScenarioStats();
    mockStats({
      ...stats,
      scenario: { ...stats.scenario, status: "draft", has_stats: false },
    });
    renderPage();

    expect(await screen.findByText("Publish this story to see stats")).toBeInTheDocument();
  });

  it("shows not found for a scenario the caller does not own", async () => {
    server.use(
      http.get(STATS_URL, () =>
        HttpResponse.json({ detail: "Scenario not found" }, { status: 404 }),
      ),
    );
    renderPage();

    expect(await screen.findByText("Story not found")).toBeInTheDocument();
  });

  it("uses the range from the URL and refetches on change", async () => {
    const { ranges } = mockStats(buildScenarioStats());
    renderPage("/studio/scn-1/stats?range=90d");
    await screen.findByRole("heading", { name: "The Hollow Cairn" });

    await userEvent.click(screen.getByRole("radio", { name: "All time" }));

    await waitFor(() => expect(ranges).toEqual(["90d", "all"]));
  });

  it("renders versions, benchmarks, end conditions and the heatmap", async () => {
    mockStats(buildScenarioStats());
    renderPage();

    expect(await screen.findByRole("heading", { name: "Versions" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "v2" })).toBeInTheDocument();
    expect(screen.getByText("You vs similar stories (median of 6)")).toBeInTheDocument();
    expect(screen.getByText("Endings reached")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Location heatmap" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Entrance/ })).toBeInTheDocument();
  });

  it("hides benchmarks and the heatmap when absent", async () => {
    mockStats(buildScenarioStats({ benchmarks: null, heatmap: [] }));
    renderPage();

    await screen.findByRole("heading", { name: "Versions" });
    expect(screen.queryByRole("heading", { name: "Benchmarks" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Location heatmap" }),
    ).not.toBeInTheDocument();
  });
});
