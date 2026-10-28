import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  ALPHA_CONSENT_VERSION,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONSENT_COPY } from "../../constants/alpha-consent";
import { useAuthStore } from "../../stores/auth.store";
import { LoginPage } from "../LoginPage";

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    error: null,
    isGoogleLoading: false,
    loginWithGoogle: vi.fn(),
    loginAsDevUser: vi.fn(),
  }),
}));

function setAuthenticatedUser(isOnboardingCompleted: boolean): void {
  useAuthStore.setState({
    accessToken: "token",
    isAuthenticated: true,
    isLoading: false,
    user: {
      user_id: "user-1",
      display_name: "Eldrin",
      onboarding_completed: isOnboardingCompleted,
    },
  });
}

function renderLogin(
  initialPath: string,
  precedingPaths: string[] = [],
): void {
  const Wrapper = createQueryWrapper();
  render(
    <Wrapper>
    <MemoryRouter
      initialEntries={[...precedingPaths, initialPath]}
      initialIndex={precedingPaths.length}
    >
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/welcome" element={<p>welcome wizard</p>} />
        <Route path="/" element={<p>home page</p>} />
        <Route path="/studio" element={<p>studio page</p>} />
      </Routes>
    </MemoryRouter>
    </Wrapper>,
  );
}

describe("LoginPage onboarding gate", () => {
  beforeEach(() => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("sends a user who has not onboarded to the wizard", async () => {
    setAuthenticatedUser(false);
    renderLogin("/login");
    expect(await screen.findByText("welcome wizard")).toBeInTheDocument();
  });

  it("sends an onboarded user to their original destination", async () => {
    setAuthenticatedUser(true);
    renderLogin("/login?redirect=%2Fstudio");
    expect(await screen.findByText("studio page")).toBeInTheDocument();
  });

  it("returns a returning user to the previous page when no target is given", async () => {
    setAuthenticatedUser(true);
    renderLogin("/login", ["/studio"]);
    expect(await screen.findByText("studio page")).toBeInTheDocument();
  });

  it("falls back to home only when there is no previous page", async () => {
    setAuthenticatedUser(true);
    renderLogin("/login");
    expect(await screen.findByText("home page")).toBeInTheDocument();
  });
});

describe("LoginPage signed out", () => {
  beforeEach(() => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("offers Google sign-in, legal links and a static accessible headline", () => {
    renderLogin("/login");
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Step into a new world");
  });
});

describe("LoginPage in alpha mode", () => {
  beforeEach(() => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    useAuthStore.setState({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("shows the consent text before the Google button", async () => {
    renderLogin("/login");

    const consentTitle = await screen.findByText(
      ALPHA_CONSENT_COPY[ALPHA_CONSENT_VERSION].title,
    );
    const googleButton = screen.getByRole("button", {
      name: /continue with google/i,
    });
    expect(
      consentTitle.compareDocumentPosition(googleButton) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});


describe("LoginPage suspension notice", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      isSuspended: true,
      user: null,
    });
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
  });

  it("explains a suspension found during a silent refresh", () => {
    renderLogin("/login");

    expect(screen.getByText(/account is suspended/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /try again/i }),
    ).not.toBeInTheDocument();
  });
});
