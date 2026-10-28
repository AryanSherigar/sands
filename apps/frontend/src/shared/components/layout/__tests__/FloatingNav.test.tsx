import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { FloatingNav } from "../FloatingNav";
import { useAuth } from "@/features/auth/hooks/useAuth";

vi.mock("@/features/auth/hooks/useAuth");

const mockUseAuth = vi.mocked(useAuth);

describe("FloatingNav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isGoogleLoading: false,
      error: null,
      loginWithGoogle: vi.fn(),
      loginAsDevUser: vi.fn(),
      logout: vi.fn(),
    });
  });

  it("renders the wordmark, nav links, search input, and sign-in link at rest", () => {
    render(
      <MemoryRouter initialEntries={["/discover"]}>
        <FloatingNav />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "sands" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /search scenarios/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /sign in/i }),
    ).toBeInTheDocument();
  });
});
