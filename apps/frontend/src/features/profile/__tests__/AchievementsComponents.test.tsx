import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { AchievementBadge } from "../components/achievements/AchievementBadge/AchievementBadge";
import { AchievementFamilySection } from "../components/achievements/AchievementFamilySection/AchievementFamilySection";
import { AchievementsTab } from "../components/tabs/AchievementsTab";
import { ACHIEVEMENT_ICONS } from "../constants/achievementIcons.constants";
import type { AchievementItem } from "../types/achievements.types";

const earned: AchievementItem = {
  key: "first-steps",
  name: "First Steps",
  family: "Journey",
  requirement: "Take your first turn",
  earned_at: "2026-10-27T00:00:00Z",
  progress: { current: 1, target: 1 },
};
const locked: AchievementItem = {
  key: "wayfarer",
  name: "Wayfarer",
  family: "Journey",
  requirement: "Take 100 turns",
  earned_at: null,
  progress: { current: 63, target: 100 },
};

describe("icons", () => {
  it("maps every catalogue key", () => {
    const keys = [
      "first-steps",
      "final-page",
      "wayfarer",
      "voyager",
      "chronicler",
      "genre-curious",
      "every-shelf",
      "five-worlds",
      "far-traveller",
      "an-ending",
      "triumph",
      "every-ending",
      "worldmaker",
      "first-readers",
      "crowd",
      "beloved",
      "five-stars",
    ];
    for (const key of keys) {
      expect(ACHIEVEMENT_ICONS[key]).toBeDefined();
    }
  });
});

describe("AchievementBadge", () => {
  it("shows an earned badge with its date and no progress bar", () => {
    render(
      <ul>
        <AchievementBadge item={earned} />
      </ul>,
    );
    expect(screen.getByText("First Steps")).toBeInTheDocument();
    expect(screen.getByText(/^Earned/)).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("shows an unearned badge with an accessible progress bar and text value", () => {
    render(
      <ul>
        <AchievementBadge item={locked} />
      </ul>,
    );
    const bar = screen.getByRole("progressbar", { name: "Wayfarer" });
    expect(bar).toHaveAttribute("aria-valuenow", "63");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText("63 / 100")).toBeInTheDocument();
  });

  it("omits progress when it is not visible (visitor view)", () => {
    render(
      <ul>
        <AchievementBadge item={{ ...earned, progress: null }} />
      </ul>,
    );
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("opens its details on click and reports expanded state", () => {
    render(
      <ul>
        <AchievementBadge item={locked} />
      </ul>,
    );
    const button = screen.getByRole("button", { name: /Wayfarer/ });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Take 100 turns")).toBeNull();
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Take 100 turns")).toBeInTheDocument();
  });

  it("does not colour badges by family and states the family as text", () => {
    const { container } = render(
      <ul>
        <AchievementBadge item={earned} />
      </ul>,
    );
    expect(screen.getByText("Journey")).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/emerald|rose|amber|violet|sky-/);
  });
});

describe("AchievementFamilySection", () => {
  it("renders a heading and one badge per item", () => {
    render(
      <AchievementFamilySection family="Journey" items={[earned, locked]} />,
    );
    expect(
      screen.getByRole("heading", { name: "Journey" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });
});

const renderTab = (props: {
  isOwnerData: boolean;
  isProgressVisible: boolean;
}) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <AchievementsTab userId="u-2" {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("AchievementsTab", () => {
  it("shows every badge and progress to the owner, grouped by family", async () => {
    server.use(
      http.get("*/v1/users/me/achievements", () =>
        HttpResponse.json([
          { ...earned },
          { ...locked },
          {
            key: "worldmaker",
            name: "Worldmaker",
            family: "Creator",
            requirement: "Publish your first story",
            earned_at: null,
            progress: { current: 0, target: 1 },
          },
        ]),
      ),
    );
    renderTab({ isOwnerData: true, isProgressVisible: true });
    expect(
      await screen.findByRole("heading", { name: "Journey" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Creator" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("progressbar")).toHaveLength(2);
  });

  it("shows only earned badges without progress to a visitor", async () => {
    server.use(
      http.get("*/v1/users/u-2/achievements", () =>
        HttpResponse.json([
          {
            key: "first-steps",
            name: "First Steps",
            family: "Journey",
            requirement: "Take your first turn",
            earned_at: "2026-10-27T00:00:00Z",
          },
        ]),
      ),
    );
    renderTab({ isOwnerData: false, isProgressVisible: false });
    expect(await screen.findByText("First Steps")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("hides unearned badges and progress for the owner previewing as a visitor, using owner data", async () => {
    let publicRequests = 0;
    server.use(
      http.get("*/v1/users/me/achievements", () =>
        HttpResponse.json([{ ...earned }, { ...locked }]),
      ),
      http.get("*/v1/users/u-2/achievements", () => {
        publicRequests += 1;
        return HttpResponse.json([]);
      }),
    );
    renderTab({ isOwnerData: true, isProgressVisible: false });
    expect(await screen.findByText("First Steps")).toBeInTheDocument();
    expect(screen.queryByText("Wayfarer")).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(publicRequests).toBe(0);
  });

  it("shows the empty state to a visitor with nothing earned", async () => {
    server.use(
      http.get("*/v1/users/u-2/achievements", () => HttpResponse.json([])),
    );
    renderTab({ isOwnerData: false, isProgressVisible: false });
    expect(
      await screen.findByText("No achievements earned yet"),
    ).toBeInTheDocument();
  });

  it("shows every badge at zero for a brand-new owner without NaN", async () => {
    const zero = Array.from({ length: 3 }, (_, index) => ({
      key: `k${index}`,
      name: `Badge ${index}`,
      family: "Journey",
      requirement: "r",
      earned_at: null,
      progress: { current: 0, target: 100 },
    }));
    server.use(
      http.get("*/v1/users/me/achievements", () => HttpResponse.json(zero)),
    );
    renderTab({ isOwnerData: true, isProgressVisible: true });
    expect(await screen.findAllByText("0 / 100")).toHaveLength(3);
    expect(document.body.textContent).not.toMatch(/NaN/);
  });

  it("shows an alert on failure", async () => {
    server.use(
      http.get(
        "*/v1/users/me/achievements",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderTab({ isOwnerData: true, isProgressVisible: true });
    expect(await screen.findByRole("alert")).toHaveTextContent(/achievements/i);
  });
});
