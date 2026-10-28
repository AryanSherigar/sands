import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { CreationsTab } from "../components/tabs/CreationsTab";
import { BookmarksTab } from "../components/tabs/BookmarksTab";
import { CampaignsTab } from "../components/tabs/CampaignsTab";
import { ReviewsTab } from "../components/tabs/ReviewsTab";

const renderWithProviders = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
};

const scenarioItem = (overrides: Record<string, unknown> = {}) => ({
  scenario_id: "sc-1",
  title: "The Grey Ledger",
  logline: "A missing ledger.",
  cover_image_url: null,
  genre_tags: ["Noir / Detective"],
  mode: "master",
  status: "published",
  rating_avg: "4.0",
  play_count: 3,
  ...overrides,
});

describe("CreationsTab", () => {
  it("shows the visitor empty state without an action", async () => {
    server.use(
      http.get("*/v1/scenarios", () => HttpResponse.json({ items: [] })),
    );
    renderWithProviders(<CreationsTab userId="u-2" isOwner={false} />);
    expect(await screen.findByText(/No stories yet/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /New Story/ })).toBeNull();
  });

  it("shows the owner empty state with a create action", async () => {
    server.use(
      http.get("*/v1/scenarios", () => HttpResponse.json({ items: [] })),
    );
    renderWithProviders(<CreationsTab userId="u-1" isOwner={true} />);
    expect(
      await screen.findByRole("link", { name: "New Story" }),
    ).toHaveAttribute("href", "/studio/new");
  });

  it("lists published scenarios and splits drafts for the owner", async () => {
    server.use(
      http.get("*/v1/scenarios", () =>
        HttpResponse.json({
          items: [
            scenarioItem(),
            scenarioItem({
              scenario_id: "sc-2",
              title: "Draft One",
              status: "draft",
            }),
          ],
        }),
      ),
    );
    renderWithProviders(<CreationsTab userId="u-1" isOwner={true} />);
    expect(await screen.findByText("The Grey Ledger")).toBeInTheDocument();
    expect(screen.queryByText("Draft One")).toBeNull();
  });

  it("shows an alert when the request fails", async () => {
    server.use(
      http.get(
        "*/v1/scenarios",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderWithProviders(<CreationsTab userId="u-2" isOwner={false} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});

describe("BookmarksTab", () => {
  it("shows the empty state", async () => {
    server.use(
      http.get("*/v1/scenarios", () => HttpResponse.json({ items: [] })),
    );
    renderWithProviders(<BookmarksTab />);
    expect(await screen.findByText("Nothing saved yet")).toBeInTheDocument();
  });

  it("renders a remove-bookmark control per card", async () => {
    server.use(
      http.get("*/v1/scenarios", () =>
        HttpResponse.json({ items: [scenarioItem()] }),
      ),
    );
    renderWithProviders(<BookmarksTab />);
    expect(
      await screen.findByRole("button", { name: "Remove bookmark" }),
    ).toBeInTheDocument();
  });
});

describe("CampaignsTab", () => {
  it("shows the empty state with an Explore stories action", async () => {
    server.use(
      http.get("*/v1/users/me/playthroughs", () => HttpResponse.json([])),
    );
    renderWithProviders(<CampaignsTab />);
    expect(await screen.findByText("No runs yet")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Explore stories" }),
    ).toHaveLength(1);
  });

  it("shows an alert when the request fails", async () => {
    server.use(
      http.get(
        "*/v1/users/me/playthroughs",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderWithProviders(<CampaignsTab />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});

describe("ReviewsTab", () => {
  it("shows No reviews yet with no action", async () => {
    server.use(http.get("*/v1/users/u-2/reviews", () => HttpResponse.json([])));
    renderWithProviders(<ReviewsTab userId="u-2" />);
    expect(await screen.findByText("No reviews yet")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("shows an alert on failure", async () => {
    server.use(
      http.get(
        "*/v1/users/u-2/reviews",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderWithProviders(<ReviewsTab userId="u-2" />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
