import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { EndingSlotItem } from "../components/endings/EndingSlotItem/EndingSlotItem";
import { ScenarioEndingsCard } from "../components/endings/ScenarioEndingsCard/ScenarioEndingsCard";
import { EndingsTab } from "../components/tabs/EndingsTab";
import type { ScenarioEndings } from "../types/endings.types";

const story: ScenarioEndings = {
  scenario_id: "sc-1",
  scenario_title: "The Cairn",
  found_count: 2,
  total_count: 3,
  slots: [
    { is_found: true, title: "Ashen", outcome_tag: "win" },
    { is_found: true, title: "Consumed", outcome_tag: "lose" },
    { is_found: false, title: null, outcome_tag: null },
  ],
};

describe("EndingSlotItem", () => {
  it("shows a found win with label and title", () => {
    render(<EndingSlotItem slot={story.slots[0]} />);
    expect(screen.getByText("Victory")).toBeInTheDocument();
    expect(screen.getByText("Ashen")).toBeInTheDocument();
  });

  it("shows a found loss as Defeat", () => {
    render(<EndingSlotItem slot={story.slots[1]} />);
    expect(screen.getByText("Defeat")).toBeInTheDocument();
  });

  it("locks an unfound slot without any name", () => {
    render(<EndingSlotItem slot={story.slots[2]} />);
    expect(screen.getByText("Undiscovered")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/null|undefined/);
  });
});

describe("ScenarioEndingsCard", () => {
  it("captions progress and links to the story", () => {
    render(
      <MemoryRouter>
        <ScenarioEndingsCard story={story} />
      </MemoryRouter>,
    );
    expect(screen.getByText("2 of 3 endings found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "The Cairn" })).toHaveAttribute(
      "href",
      "/scenario/sc-1",
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("uses the singular for one ending", () => {
    render(
      <MemoryRouter>
        <ScenarioEndingsCard
          story={{
            ...story,
            found_count: 0,
            total_count: 1,
            slots: [story.slots[2]],
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("0 of 1 ending found")).toBeInTheDocument();
  });
});

const renderTab = () =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <EndingsTab />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("EndingsTab", () => {
  it("lists each story", async () => {
    server.use(
      http.get("*/v1/users/me/endings", () =>
        HttpResponse.json({ scenarios: [story] }),
      ),
    );
    renderTab();
    expect(await screen.findByText("The Cairn")).toBeInTheDocument();
  });

  it("shows the empty state with one action", async () => {
    server.use(
      http.get("*/v1/users/me/endings", () =>
        HttpResponse.json({ scenarios: [] }),
      ),
    );
    renderTab();
    expect(
      await screen.findByText("Finish a story to discover endings"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Explore stories" }),
    ).toHaveAttribute("href", "/discover");
  });

  it("shows an alert on failure", async () => {
    server.use(
      http.get(
        "*/v1/users/me/endings",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderTab();
    expect(await screen.findByRole("alert")).toHaveTextContent(/endings/i);
  });
});
