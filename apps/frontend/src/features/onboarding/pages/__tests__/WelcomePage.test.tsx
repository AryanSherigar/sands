import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { READER_THEME_STORAGE_KEY } from "@/shared/constants/reader-preferences";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { server } from "@/test/msw/server";
import { WelcomePage } from "../WelcomePage";

const API_URL = "http://localhost:8000";
const ONBOARDING_URL = `${API_URL}/v1/users/me/onboarding`;

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

function renderWizard(initialPath = "/welcome"): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/welcome" element={<WelcomePage />} />
          <Route path="/" element={<p>home page</p>} />
          <Route path="/studio" element={<p>studio page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockOnboardingEndpoint(): { getPayload: () => unknown } {
  let payload: unknown = null;
  server.use(
    http.post(ONBOARDING_URL, async ({ request }) => {
      payload = await request.json();
      const body = payload as { display_name?: string };
      return HttpResponse.json({
        display_name: body.display_name ?? "Eldrin",
        preferred_genres: [],
        onboarding_completed_at: "2026-10-27T00:00:00Z",
      });
    }),
  );
  return { getPayload: () => payload };
}

async function startWizard(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Get started" }));
  await screen.findByRole("heading", { name: "What do you like to read?" });
}

async function skipTo(
  user: ReturnType<typeof userEvent.setup>,
  headingName: string,
) {
  await user.click(screen.getByRole("button", { name: "Skip" }));
  await screen.findByRole("heading", { name: headingName });
}

describe("WelcomePage", () => {
  beforeEach(() => {
    localStorage.clear();
    useReaderPreferencesStore.setState({
      fontId: null,
      theme: "dark-velvet",
      fontSize: "medium",
      lineHeight: "comfortable",
    });
    setUser(false);
  });

  it("limits genre picks to three, keeps Next enabled with none, and explains the cap", async () => {
    const user = userEvent.setup();
    renderWizard();
    await startWizard(user);

    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
    await user.click(screen.getByRole("checkbox", { name: "Horror" }));
    await user.click(screen.getByRole("checkbox", { name: "Sci-Fi" }));
    await user.click(screen.getByRole("checkbox", { name: "Mystery" }));

    expect(screen.getByRole("checkbox", { name: "Cyberpunk" })).toBeDisabled();
    expect(screen.getByText("Up to 3")).toBeInTheDocument();
    expect(screen.getByText("3 of 3 selected")).toBeInTheDocument();
  });

  it("lets the user skip the profile step without a display name", async () => {
    const user = userEvent.setup();
    renderWizard();
    await startWizard(user);
    await skipTo(user, "Who are you, adventurer?");

    await user.clear(screen.getByLabelText(/display name/i));
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
  });

  it("shows a live profile preview and caps the bio at 160 characters", async () => {
    const user = userEvent.setup();
    renderWizard();
    await startWizard(user);
    await skipTo(user, "Who are you, adventurer?");

    await user.clear(screen.getByLabelText(/display name/i));
    await user.type(screen.getByLabelText(/display name/i), "Archmage");

    expect(
      within(screen.getByTestId("profile-preview")).getByText("Archmage"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/bio/i)).toHaveAttribute("maxLength", "160");
  });

  it("offers Set up later on every input step", async () => {
    const user = userEvent.setup();
    renderWizard();
    expect(screen.getByRole("button", { name: "Set up later" })).toBeVisible();

    await startWizard(user);
    expect(screen.getByRole("button", { name: "Set up later" })).toBeVisible();
    await skipTo(user, "Who are you, adventurer?");
    expect(screen.getByRole("button", { name: "Set up later" })).toBeVisible();
    await skipTo(user, "How do you like to read?");
    expect(screen.getByRole("button", { name: "Set up later" })).toBeVisible();
  });

  it("saves everything once at the end and offers the genre-filtered Discover link", async () => {
    const endpoint = mockOnboardingEndpoint();
    const user = userEvent.setup();
    renderWizard();

    await startWizard(user);
    await user.click(screen.getByRole("checkbox", { name: "Horror" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByRole("heading", { name: "Who are you, adventurer?" });
    await user.clear(screen.getByLabelText(/display name/i));
    await user.type(screen.getByLabelText(/display name/i), "Archmage");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByRole("heading", { name: "How do you like to read?" });
    await user.click(screen.getByRole("button", { name: "Sepia" }));
    await user.click(screen.getByRole("button", { name: "Relaxed" }));
    await user.click(screen.getByRole("button", { name: "Next" }));

    const link = await screen.findByRole("link", { name: "Explore stories" });
    expect(link).toHaveAttribute("href", "/discover?genre=Horror");
    expect(screen.getByRole("link", { name: "Go home" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(endpoint.getPayload()).toEqual({
      preferred_genres: ["Horror"],
      display_name: "Archmage",
    });
    expect(useAuthStore.getState().user?.onboarding_completed).toBe(true);
    expect(useAuthStore.getState().user?.display_name).toBe("Archmage");
    expect(localStorage.getItem(READER_THEME_STORAGE_KEY)).toBe(
      "antique-sepia",
    );
    expect(useReaderPreferencesStore.getState().lineHeight).toBe("relaxed");
  });

  it("updates the reading sample as choices change", async () => {
    const user = userEvent.setup();
    renderWizard();
    await startWizard(user);
    await skipTo(user, "Who are you, adventurer?");
    await skipTo(user, "How do you like to read?");

    const preview = screen.getByTestId("reader-preview");
    expect(preview).toHaveAttribute("aria-live", "polite");
    await user.click(screen.getByRole("button", { name: "Large" }));
    await user.click(screen.getByRole("button", { name: "Compact" }));
    expect(preview).toHaveClass("text-[22px]", "leading-normal");
  });

  it("completes with what is filled and returns to the original destination on Set up later", async () => {
    const endpoint = mockOnboardingEndpoint();
    const user = userEvent.setup();
    renderWizard("/welcome?redirect=%2Fstudio");

    await user.click(screen.getByRole("button", { name: "Set up later" }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Set up later",
      }),
    );

    expect(await screen.findByText("studio page")).toBeInTheDocument();
    expect(endpoint.getPayload()).toEqual({
      preferred_genres: [],
      display_name: "Eldrin",
    });
  });

  it("keeps the wizard open, shows an error, and offers Retry when saving fails", async () => {
    server.use(
      http.post(ONBOARDING_URL, () => new HttpResponse(null, { status: 500 })),
    );
    const user = userEvent.setup();
    renderWizard();

    await startWizard(user);
    await skipTo(user, "Who are you, adventurer?");
    await skipTo(user, "How do you like to read?");
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't save/i);
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
    expect(useAuthStore.getState().user?.onboarding_completed).toBe(false);
  });

  it("sends already-onboarded users away", async () => {
    setUser(true);
    renderWizard();

    await waitFor(() =>
      expect(screen.getByText("home page")).toBeInTheDocument(),
    );
  });
});
