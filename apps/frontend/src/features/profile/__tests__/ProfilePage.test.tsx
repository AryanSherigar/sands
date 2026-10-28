import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { UserResponse } from "@/features/auth/types/auth.types";
import { ProfilePage } from "../pages/ProfilePage";
import { overviewBody } from "./fixtures/overview";
import { useProfilePreviewStore } from "../stores/profilePreview.store";

const OWNER = { user_id: "u-1" } as unknown as UserResponse;

const profileBody = (userId: string) => ({
  user_id: userId,
  display_name: "Elminster",
  bio: "Archmage",
  avatar_url: null,
  banner_url: null,
  created_at: "2026-10-27T00:00:00Z",
  stats: {
    campaigns_played_count: 7,
    victories_count: 5,
    total_turns_taken: 84,
    scenarios_authored_count: 3,
    total_plays_received: 120,
  },
});

const renderPage = (path: string) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/profile/:id" element={<ProfilePage />} />
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

beforeEach(() => {
  useProfilePreviewStore.setState({ isPreviewingAsVisitor: false });
  useAuthStore.setState({
    user: OWNER,
    isAuthenticated: true,
    isLoading: false,
  });
  server.use(
    http.get("*/v1/users/me", () => HttpResponse.json(profileBody("u-1"))),
    http.get("*/v1/users/u-2", () => HttpResponse.json(profileBody("u-2"))),
    http.get("*/v1/users/u-1", () => HttpResponse.json(profileBody("u-1"))),
    http.get("*/v1/scenarios", () => HttpResponse.json({ items: [] })),
    http.get("*/v1/users/*/reviews", () => HttpResponse.json([])),
    http.get("*/v1/users/me/playthroughs", () => HttpResponse.json([])),
    http.get("*/v1/users/me/overview", () => HttpResponse.json(overviewBody)),
    http.get("*/v1/users/me/endings", () =>
      HttpResponse.json({ scenarios: [] }),
    ),
    http.get("*/v1/users/me/achievements", () => HttpResponse.json([])),
    http.get("*/v1/users/u-2/achievements", () => HttpResponse.json([])),
  );
});

describe("ProfilePage", () => {
  it("shows the seven owner tabs with Overview selected by default", async () => {
    renderPage("/profile");
    expect(
      await screen.findByRole("tab", { name: "Overview" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(
      await screen.findByRole("tab", { name: "Campaigns" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Bookmarks" })).toBeInTheDocument();
    expect(
      screen.getByRole("radiogroup", { name: "Viewing as" }),
    ).toBeInTheDocument();
  });

  it("gives a visitor only public tabs and no Viewing-as bar", async () => {
    renderPage("/profile/u-2");
    expect(
      await screen.findByRole("tab", { name: "Creations" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Campaigns" })).toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "Viewing as" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit profile" })).toBeNull();
  });

  it("falls back to Creations when a visitor opens an owner-only tab param", async () => {
    renderPage("/profile/u-2?tab=campaigns");
    const creations = await screen.findByRole("tab", { name: "Creations" });
    expect(creations).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Campaigns" })).toBeNull();
  });

  it("honours a valid ?tab= for the owner", async () => {
    renderPage("/profile?tab=reviews");
    expect(await screen.findByRole("tab", { name: "Reviews" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("previewing as visitor hides owner-only tabs, Edit profile, and the ribbon", async () => {
    renderPage("/profile");
    await screen.findByText("Turns Taken");
    fireEvent.click(screen.getByRole("radio", { name: "Public Visitor" }));
    expect(screen.queryByRole("tab", { name: "Overview" })).toBeNull();
    expect(screen.queryByText("Turns Taken")).toBeNull();
    expect(screen.queryByRole("tab", { name: "Campaigns" })).toBeNull();
    expect(screen.getByRole("tab", { name: "Creations" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByRole("button", { name: "Edit profile" })).toBeNull();
    expect(screen.queryByText("Turns Taken")).toBeNull();
  });

  it("resets the preview when the page unmounts", async () => {
    const { unmount } = renderPage("/profile");
    await screen.findByRole("tab", { name: "Campaigns" });
    fireEvent.click(screen.getByRole("radio", { name: "Public Visitor" }));
    unmount();
    expect(useProfilePreviewStore.getState().isPreviewingAsVisitor).toBe(false);
  });

  it("shows a not-found state when the profile 404s", async () => {
    server.use(
      http.get("*/v1/users/u-9", () => new HttpResponse(null, { status: 404 })),
    );
    renderPage("/profile/u-9");
    expect(
      await screen.findByText("This profile doesn't exist"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to Discover" }),
    ).toBeInTheDocument();
  });

  it("redirects an unauthenticated /profile to login", async () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    renderPage("/profile");
    expect(await screen.findByText("login page")).toBeInTheDocument();
  });

  it("keeps the owner's ?tab= on their own /profile/:id while auth is still loading", async () => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
    renderPage("/profile/u-1?tab=campaigns");
    await act(async () => {
      useAuthStore.setState({
        user: OWNER,
        isAuthenticated: true,
        isLoading: false,
      });
    });
    expect(
      await screen.findByRole("tab", { name: "Campaigns" }),
    ).toHaveAttribute("aria-selected", "true");
  });

  it("leaves visitor preview when navigated to an owner-only tab", async () => {
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <MemoryRouter initialEntries={["/profile"]}>
          <Link to="/profile?tab=bookmarks">menu bookmarks</Link>
          <Routes>
            <Route path="/profile" element={<ProfilePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await screen.findByRole("tab", { name: "Campaigns" });
    fireEvent.click(screen.getByRole("radio", { name: "Public Visitor" }));
    expect(screen.queryByRole("tab", { name: "Bookmarks" })).toBeNull();
    fireEvent.click(screen.getByText("menu bookmarks"));
    expect(
      await screen.findByRole("tab", { name: "Bookmarks" }),
    ).toHaveAttribute("aria-selected", "true");
  });

  it("starts the edit modal fresh each time it opens", async () => {
    renderPage("/profile");
    fireEvent.click(
      await screen.findByRole("button", { name: "Edit profile" }),
    );
    fireEvent.change(screen.getByDisplayValue("Archmage"), {
      target: { value: "Discarded" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));
    await waitFor(() =>
      expect(screen.getByDisplayValue("Archmage")).toBeInTheDocument(),
    );
  });

  it("a visitor never requests the owner overview", async () => {
    let overviewRequests = 0;
    server.use(
      http.get("*/v1/users/me/overview", () => {
        overviewRequests += 1;
        return HttpResponse.json(overviewBody);
      }),
    );
    renderPage("/profile/u-2");
    await screen.findByRole("tab", { name: "Creations" });
    expect(overviewRequests).toBe(0);
  });

  it("selects the Endings tab for the owner from ?tab=endings", async () => {
    renderPage("/profile?tab=endings");
    expect(await screen.findByRole("tab", { name: "Endings" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      await screen.findByText("Finish a story to discover endings"),
    ).toBeInTheDocument();
  });

  it("a visitor on ?tab=endings falls back to Creations and never requests endings", async () => {
    let endingsRequests = 0;
    server.use(
      http.get("*/v1/users/me/endings", () => {
        endingsRequests += 1;
        return HttpResponse.json({ scenarios: [] });
      }),
    );
    renderPage("/profile/u-2?tab=endings");
    expect(
      await screen.findByRole("tab", { name: "Creations" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("tab", { name: "Endings" })).toBeNull();
    expect(endingsRequests).toBe(0);
  });

  it("selects the Achievements tab for the owner and reads only the owner endpoint", async () => {
    let publicRequests = 0;
    server.use(
      http.get("*/v1/users/u-1/achievements", () => {
        publicRequests += 1;
        return HttpResponse.json([]);
      }),
    );
    renderPage("/profile?tab=achievements");
    expect(
      await screen.findByRole("tab", { name: "Achievements" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(
      await screen.findByText("No achievements earned yet"),
    ).toBeInTheDocument();
    expect(publicRequests).toBe(0);
  });

  it("gives a visitor the Achievements tab backed by the public endpoint only", async () => {
    let ownerRequests = 0;
    server.use(
      http.get("*/v1/users/me/achievements", () => {
        ownerRequests += 1;
        return HttpResponse.json([]);
      }),
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
    renderPage("/profile/u-2?tab=achievements");
    expect(
      await screen.findByRole("tab", { name: "Achievements" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("First Steps")).toBeInTheDocument();
    expect(ownerRequests).toBe(0);
  });

  it("keeps Achievements when the owner previews as a visitor but hides unearned badges and progress", async () => {
    server.use(
      http.get("*/v1/users/me/achievements", () =>
        HttpResponse.json([
          {
            key: "first-steps",
            name: "First Steps",
            family: "Journey",
            requirement: "Take your first turn",
            earned_at: "2026-10-27T00:00:00Z",
            progress: { current: 1, target: 1 },
          },
          {
            key: "wayfarer",
            name: "Wayfarer",
            family: "Journey",
            requirement: "Take 100 turns",
            earned_at: null,
            progress: { current: 63, target: 100 },
          },
        ]),
      ),
    );
    renderPage("/profile?tab=achievements");
    expect(await screen.findByText("Wayfarer")).toBeInTheDocument();
    expect(screen.getAllByRole("progressbar")).toHaveLength(1);

    fireEvent.click(screen.getByRole("radio", { name: "Public Visitor" }));

    expect(screen.getByRole("tab", { name: "Achievements" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.queryByText("Wayfarer")).toBeNull();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByText("First Steps")).toBeInTheDocument();
  });
});
