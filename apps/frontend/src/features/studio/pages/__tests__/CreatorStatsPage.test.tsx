import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { buildOverview } from "../../test/statsFixtures";
import type { CreatorStatsOverviewResponse } from "../../types/stats.types";
import { CreatorStatsPage } from "../CreatorStatsPage";

const OVERVIEW_URL = "http://localhost:8000/v1/creators/me/stats";

function mockOverview(body: CreatorStatsOverviewResponse): { ranges: string[] } {
  const ranges: string[] = [];
  server.use(
    http.get(OVERVIEW_URL, ({ request }) => {
      ranges.push(new URL(request.url).searchParams.get("range") ?? "");
      return HttpResponse.json(body);
    }),
  );
  return { ranges };
}

function renderPage(): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/studio/stats"]}>
        <Routes>
          <Route path="/studio/stats" element={<CreatorStatsPage />} />
          <Route path="/studio/:id/stats" element={<p>deep stats page</p>} />
          <Route path="/studio" element={<p>studio page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CreatorStatsPage", () => {
  it("shows headline tiles, the plays chart and the scenario table", async () => {
    mockOverview(buildOverview());
    renderPage();

    expect(await screen.findByText("Completion %")).toBeInTheDocument();
    expect(screen.getByText("Avg rating")).toBeInTheDocument();
    expect(screen.getByText("Plays over time")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /The Hollow Cairn/ })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Plays" })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("shows the publish empty state when nothing is published", async () => {
    mockOverview(buildOverview({ has_published_scenarios: false, scenarios: [] }));
    renderPage();

    expect(await screen.findByText("Publish a story to see stats")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to Studio" }));
    expect(await screen.findByText("studio page")).toBeInTheDocument();
  });

  it("hides the chart under the sample threshold", async () => {
    mockOverview(buildOverview({ is_sample_sufficient: false }));
    renderPage();

    expect(await screen.findByText("Stats appear after 5 plays.")).toBeInTheDocument();
    expect(screen.queryByText("Plays over time")).not.toBeInTheDocument();
  });

  it("requests the range chosen in the picker", async () => {
    const { ranges } = mockOverview(buildOverview());
    renderPage();
    await screen.findByText("Completion %");

    await userEvent.click(screen.getByRole("radio", { name: "7d" }));

    await waitFor(() => expect(ranges).toContain("7d"));
    expect(ranges[0]).toBe("30d");
  });

  it("opens deep stats when a row is clicked", async () => {
    mockOverview(buildOverview());
    renderPage();

    await userEvent.click(await screen.findByRole("row", { name: /The Hollow Cairn/ }));

    expect(await screen.findByText("deep stats page")).toBeInTheDocument();
  });

  it("offers a retry when loading fails", async () => {
    server.use(http.get(OVERVIEW_URL, () => new HttpResponse(null, { status: 500 })));
    renderPage();

    expect(await screen.findByText("Couldn't load stats")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
