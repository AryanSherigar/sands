import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { MatureAttestationDialog } from "@/shared/components/MatureAttestationDialog/MatureAttestationDialog";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useMatureAttestationStore } from "@/shared/stores/matureAttestation.store";
import { server } from "@/test/msw/server";
import { SettingsPage } from "../pages/SettingsPage";

const USERS_ME_URL = "http://localhost:8000/v1/users/me";

function setSignedIn(showMature: boolean): void {
  useAuthStore.setState({
    accessToken: "token",
    isAuthenticated: true,
    isLoading: false,
    user: {
      user_id: "user-1",
      display_name: "Eldrin",
      onboarding_completed: true,
      show_mature: showMature,
    },
  });
}

function renderSettings(): void {
  server.use(
    http.get(USERS_ME_URL, () =>
      HttpResponse.json({
        created_at: "2026-10-27T00:00:00Z",
        voice_output_enabled: false,
      }),
    ),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
        <MatureAttestationDialog />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockPatch(requests: unknown[] = [], isFailing = false): void {
  server.use(
    http.patch(USERS_ME_URL, async ({ request }) => {
      const body = (await request.json()) as { show_mature: boolean };
      requests.push(body);
      if (isFailing) return new HttpResponse(null, { status: 500 });
      return HttpResponse.json({ show_mature: body.show_mature });
    }),
  );
}

const getSwitch = (): HTMLElement =>
  screen.getByRole("switch", { name: "Show mature content" });

describe("SettingsPage", () => {
  beforeEach(() => {
    useMatureAttestationStore.setState({ isOpen: false, resolvePending: null });
  });

  it("shows the mature switch off by default under a Content section", () => {
    setSignedIn(false);
    renderSettings();

    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Content preferences" })).toBeInTheDocument();
    expect(getSwitch()).not.toBeChecked();
  });

  it("has no global Save button", () => {
    setSignedIn(false);
    renderSettings();

    expect(screen.queryByRole("button", { name: /^save/i })).not.toBeInTheDocument();
  });

  it("requires the 18+ confirmation before turning mature content on", async () => {
    const requests: unknown[] = [];
    mockPatch(requests);
    setSignedIn(false);
    renderSettings();

    await userEvent.click(getSwitch());

    const confirm = await screen.findByRole("button", { name: "Show mature content" });
    expect(confirm).toBeDisabled();
    expect(requests).toEqual([]);

    await userEvent.click(screen.getByRole("checkbox", { name: "I confirm I am 18 or older" }));
    await userEvent.click(confirm);

    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(requests).toEqual([{ show_mature: true }]);
    expect(useAuthStore.getState().user?.show_mature).toBe(true);
    expect(getSwitch()).toBeChecked();
  });

  it("changes nothing when the confirmation is cancelled", async () => {
    const requests: unknown[] = [];
    mockPatch(requests);
    setSignedIn(false);
    renderSettings();

    await userEvent.click(getSwitch());
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument(),
    );
    expect(requests).toEqual([]);
    expect(getSwitch()).not.toBeChecked();
    expect(useAuthStore.getState().user?.show_mature).toBe(false);
  });

  it("turns mature content off immediately without asking again", async () => {
    const requests: unknown[] = [];
    mockPatch(requests);
    setSignedIn(true);
    renderSettings();

    await userEvent.click(getSwitch());

    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(requests).toEqual([{ show_mature: false }]);
    expect(screen.queryByRole("checkbox", { name: /18 or older/ })).not.toBeInTheDocument();
    expect(useAuthStore.getState().user?.show_mature).toBe(false);
  });

  it("reverts and offers Retry inline when saving fails", async () => {
    mockPatch([], true);
    setSignedIn(true);
    renderSettings();

    await userEvent.click(getSwitch());

    expect(await screen.findByRole("alert")).toHaveTextContent("Retry");
    expect(getSwitch()).toBeChecked();
    expect(useAuthStore.getState().user?.show_mature).toBe(true);

    const requests: unknown[] = [];
    mockPatch(requests);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(requests).toEqual([{ show_mature: false }]);
    expect(getSwitch()).not.toBeChecked();
  });

  it("explains the three age ratings", () => {
    setSignedIn(false);
    renderSettings();

    expect(screen.getByText("Suitable for everyone.")).toBeInTheDocument();
    expect(screen.getByText("All Ages")).toBeInTheDocument();
    expect(screen.getByText("Teen")).toBeInTheDocument();
  });

  it("renders every section and the section navigation", () => {
    setSignedIn(false);
    renderSettings();

    const [nav] = screen.getAllByRole("navigation", { name: "Settings sections" });
    for (const label of ["Account", "Reading", "Content", "Notifications"]) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { level: 2, name: "Account" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Reading defaults" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Notifications" })).toBeInTheDocument();
  });

  it("shows the member-since date from the account summary", async () => {
    setSignedIn(false);
    renderSettings();

    expect(await screen.findByText(/Member since .*2026/)).toBeInTheDocument();
  });

  it("changes the reading theme and text size instantly", async () => {
    setSignedIn(false);
    renderSettings();

    await userEvent.click(screen.getByRole("radio", { name: "Sepia" }));
    await userEvent.click(screen.getByRole("radio", { name: "Large (22px)" }));

    expect(useReaderPreferencesStore.getState().theme).toBe("antique-sepia");
    expect(useReaderPreferencesStore.getState().fontSize).toBe("large");
    expect(screen.getByRole("radio", { name: "Sepia" })).toBeChecked();
  });

  it("falls back to the story's font and can pick a fixed narration font", async () => {
    setSignedIn(false);
    renderSettings();
    const select = screen.getByLabelText("Narration typography");

    expect(select).toHaveValue("");
    await userEvent.selectOptions(select, "cinzel");

    expect(useReaderPreferencesStore.getState().fontId).toBe("cinzel");
  });

  it("shows an inline storage error with Retry when localStorage is unavailable", async () => {
    setSignedIn(false);
    renderSettings();
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    await userEvent.click(screen.getByRole("radio", { name: "Sepia" }));

    expect(await screen.findByText("Couldn't save locally")).toBeInTheDocument();
    expect(useReaderPreferencesStore.getState().theme).toBe("antique-sepia");
    setItem.mockRestore();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(screen.queryByText("Couldn't save locally")).not.toBeInTheDocument();
  });
});
