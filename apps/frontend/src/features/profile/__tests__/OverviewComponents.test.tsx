import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { LifetimeStats } from "../components/overview/LifetimeStats/LifetimeStats";
import { WeeklyActivityDots } from "../components/overview/WeeklyActivityDots/WeeklyActivityDots";
import { ContinueRow } from "../components/overview/ContinueRow/ContinueRow";
import { RecentMilestones } from "../components/overview/RecentMilestones/RecentMilestones";
import { OverviewTab } from "../components/tabs/OverviewTab";
import { makeRun, overviewBody } from "./fixtures/overview";

const NOW = new Date("2026-10-27T12:00:00Z");

const withRouter = (ui: React.ReactElement) => (
  <MemoryRouter>{ui}</MemoryRouter>
);

describe("LifetimeStats", () => {
  it("renders the five tiles with their subtext", () => {
    render(
      <LifetimeStats
        stats={{
          turns_taken: 1420,
          stories_completed: 8,
          endings_found: 14,
          endings_total: 32,
          worlds_played: 19,
          campaigns_count: 19,
          genres_explored: [
            "Noir / Detective",
            "Sci-Fi",
            "High Fantasy",
            "Horror",
            "Mystery",
            "Cyberpunk",
          ],
        }}
      />,
    );
    expect(screen.getByText("Turns Taken")).toBeInTheDocument();
    expect(screen.getByText("1,420")).toBeInTheDocument();
    expect(screen.getByText("Across 19 campaigns")).toBeInTheDocument();
    expect(screen.getByText("Stories Completed")).toBeInTheDocument();
    expect(screen.getByText("Endings Found")).toBeInTheDocument();
    expect(screen.getByText("/ 32")).toBeInTheDocument();
    expect(screen.getByText("43.8% completion")).toBeInTheDocument();
    expect(screen.getByText("Worlds Played")).toBeInTheDocument();
    expect(screen.getByText("Genres Explored")).toBeInTheDocument();
    expect(
      screen.getByText("Noir / Detective, Sci-Fi, High Fantasy +3"),
    ).toBeInTheDocument();
  });

  it("renders zeros for a new user without blanking", () => {
    render(
      <LifetimeStats
        stats={{
          turns_taken: 0,
          stories_completed: 0,
          endings_found: 0,
          endings_total: 0,
          worlds_played: 0,
          campaigns_count: 0,
          genres_explored: [],
        }}
      />,
    );
    expect(screen.getAllByText("0")).toHaveLength(5);
    expect(screen.getByText("None yet")).toBeInTheDocument();
    expect(screen.getByText("No endings yet")).toBeInTheDocument();
    expect(screen.queryByText(/\/ 0/)).toBeNull();
    expect(document.body.textContent).not.toMatch(/NaN/);
  });
});

describe("WeeklyActivityDots", () => {
  it("shows caption, seven dots and a text alternative", () => {
    render(
      <WeeklyActivityDots
        activity={{
          week_start: "2026-10-27",
          played_days: [true, true, false, false, true, false, false],
          played_day_count: 3,
        }}
      />,
    );
    expect(screen.getByText("Played 3 days this week")).toBeInTheDocument();
    expect(screen.getAllByTestId("weekly-dot")).toHaveLength(7);
    expect(
      screen.getByText("Played on Monday, Tuesday and Friday this week."),
    ).toHaveClass("sr-only");
  });

  it("uses quiet copy when nothing was played", () => {
    render(
      <WeeklyActivityDots
        activity={{
          week_start: "2026-10-27",
          played_days: [false, false, false, false, false, false, false],
          played_day_count: 0,
        }}
      />,
    );
    expect(screen.getByText("No stories this week yet")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/streak|broke|missed/i);
  });
});

describe("ContinueRow", () => {
  it("makes only the first Continue primary and links to the play screen", () => {
    render(
      withRouter(
        <ContinueRow
          now={NOW}
          runs={[
            makeRun(),
            makeRun({
              playthrough_id: "pt-2",
              scenario_title: "Substratum 9",
              turn_count: 8,
              primary_genre: "Sci-Fi",
              checkpoint: null,
              narration_excerpt: null,
            }),
          ]}
        />,
      ),
    );
    const links = screen.getAllByRole("link", { name: /^Continue/ });
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", "/play/pt-1");
    expect(links[0].className).toContain("bg-primary");
    expect(links[1].className).not.toContain("bg-primary");
    expect(links[0].closest('[class*="[--accent"]')).toBeNull();
    expect(screen.getByText("Act II: The Slipway")).toBeInTheDocument();
    expect(screen.getByText("Rain slicks the wharf.")).toBeInTheDocument();
    expect(screen.getByText("Turn 14 · 2h ago")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "All active runs" }),
    ).toHaveAttribute("href", "/profile?tab=campaigns");
  });

  it("omits missing act label, excerpt and genre without printing null", () => {
    render(
      withRouter(
        <ContinueRow
          now={NOW}
          runs={[
            makeRun({
              checkpoint: null,
              narration_excerpt: null,
              primary_genre: null,
              scenario_mode: "newbie",
            }),
          ]}
        />,
      ),
    );
    expect(screen.getByText("NEWBIE MODE")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/null|undefined/);
  });

  it("shows a one-action empty state when there are no active runs", () => {
    render(withRouter(<ContinueRow now={NOW} runs={[]} />));
    expect(screen.getByText("No active runs")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Explore stories" }),
    ).toHaveAttribute("href", "/discover");
  });
});

describe("RecentMilestones", () => {
  it("shows an empty state before any achievement exists", () => {
    render(withRouter(<RecentMilestones milestones={[]} />));
    expect(screen.getByText("No milestones yet")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("lists milestones and links to the achievements tab", () => {
    render(
      withRouter(
        <RecentMilestones
          milestones={[
            {
              key: "first-steps",
              name: "First Steps",
              earned_at: "2026-10-27T00:00:00Z",
            },
          ]}
        />,
      ),
    );
    expect(screen.getByText("First Steps")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View all/ })).toHaveAttribute(
      "href",
      "/profile?tab=achievements",
    );
  });
});

const renderOverviewTab = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <OverviewTab />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("OverviewTab", () => {
  it("renders every section from one response", async () => {
    server.use(
      http.get("*/v1/users/me/overview", () => HttpResponse.json(overviewBody)),
    );
    renderOverviewTab();
    expect(await screen.findByText("Turns Taken")).toBeInTheDocument();
    expect(screen.getByText("Weekly Rhythm")).toBeInTheDocument();
    expect(screen.getByText("Continue Your Narrative")).toBeInTheDocument();
    expect(screen.getByText("Recent Milestones")).toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    server.use(
      http.get(
        "*/v1/users/me/overview",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderOverviewTab();
    expect(await screen.findByRole("alert")).toHaveTextContent(/overview/i);
  });

  it("shows a busy skeleton while loading", () => {
    server.use(http.get("*/v1/users/me/overview", () => new Promise(() => {})));
    renderOverviewTab();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });
});
