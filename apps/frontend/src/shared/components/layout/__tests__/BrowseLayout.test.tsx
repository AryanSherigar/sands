import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BrowseLayout } from "../BrowseLayout";
import { useAuth } from "@/features/auth/hooks/useAuth";
import type { UserResponse } from "@/features/auth/types/auth.types";

vi.mock("@/shared/hooks/useIsAlphaMode", () => ({
  useIsAlphaMode: () => false,
}));

vi.mock("@/features/auth/hooks/useAuth");

const mockUseAuth = vi.mocked(useAuth);

const setAuth = (user: UserResponse | null, isLoading = false): void => {
  mockUseAuth.mockReturnValue({
    user,
    isAuthenticated: user !== null,
    isLoading,
    isGoogleLoading: false,
    error: null,
    loginWithGoogle: vi.fn(),
    loginAsDevUser: vi.fn(),
    logout: vi.fn(),
  });
};

const setDesktop = (isDesktop: boolean): void => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: isDesktop,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
};

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<BrowseLayout />}>
          <Route path="/" element={<p>home page</p>} />
          <Route path="/discover" element={<p>discover page</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

describe("BrowseLayout", () => {
  beforeEach(() => {
    setAuth(null);
    setDesktop(true);
  });

  it("renders the skip link before the primary nav", () => {
    renderAt("/discover");
    expect(screen.getByRole("link", { name: /skip to content/i })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("marks the active desktop link with aria-current", () => {
    renderAt("/discover");
    expect(screen.getByRole("link", { name: "Discover" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("renders exactly one primary nav on desktop", () => {
    renderAt("/discover");
    expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1);
  });

  it("shows the footer on Home only", () => {
    const { unmount } = renderAt("/");
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    unmount();
    renderAt("/discover");
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("shows Sign in when signed out and a skeleton while auth loads", () => {
    const { unmount } = renderAt("/discover");
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    unmount();
    setAuth(null, true);
    renderAt("/discover");
    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("focuses search with the slash key", async () => {
    renderAt("/discover");
    await userEvent.keyboard("/");
    expect(screen.getByRole("searchbox", { name: /search stories/i })).toHaveFocus();
  });

  it("opens the avatar menu with arrow-key navigation", async () => {
    setAuth({ user_id: "u1", display_name: "Ada", onboarding_completed: true });
    renderAt("/discover");
    await userEvent.click(screen.getByRole("button", { name: /account menu/i }));
    expect(screen.getByRole("menuitem", { name: "View profile" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "My scenarios" })).toHaveFocus();
    expect(screen.getByRole("menuitem", { name: "Creator stats" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Settings" })).toHaveAttribute(
      "href",
      "/settings",
    );
  });

  it("renders the bottom tab bar instead of the top nav on mobile", () => {
    setDesktop(false);
    renderAt("/discover");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav).toHaveTextContent("Sign in");
    expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1);
  });
});
