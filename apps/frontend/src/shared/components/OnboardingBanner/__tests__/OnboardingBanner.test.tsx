import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { server } from "@/test/msw/server";
import { OnboardingBanner } from "../OnboardingBanner";

const ONBOARDING_URL = "http://localhost:8000/v1/users/me/onboarding";

function setUser(isOnboardingCompleted: boolean): void {
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

function renderBanner(): void {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <OnboardingBanner />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OnboardingBanner", () => {
  beforeEach(() => setUser(false));

  it("links to the wizard when onboarding is incomplete", () => {
    renderBanner();

    expect(screen.getByRole("link", { name: "Start" })).toHaveAttribute(
      "href",
      "/welcome",
    );
  });

  it("renders nothing once onboarding is complete", () => {
    setUser(true);
    renderBanner();

    expect(screen.queryByText(/finish setting up/i)).not.toBeInTheDocument();
  });

  it("marks onboarding complete and hides itself when dismissed", async () => {
    server.use(
      http.post(ONBOARDING_URL, () =>
        HttpResponse.json({
          display_name: "Eldrin",
          preferred_genres: [],
          onboarding_completed_at: "2026-10-27T00:00:00Z",
        }),
      ),
    );
    const user = userEvent.setup();
    renderBanner();

    await user.click(screen.getByRole("button", { name: /dismiss/i }));

    await waitFor(() =>
      expect(useAuthStore.getState().user?.onboarding_completed).toBe(true),
    );
    expect(screen.queryByText(/finish setting up/i)).not.toBeInTheDocument();
  });
});
