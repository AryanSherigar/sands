import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useToastStore } from "@/shared/stores/toast.store";
import { server } from "@/test/msw/server";
import { DeleteAccountDialog } from "../components/DeleteAccountDialog/DeleteAccountDialog";

const reauthenticateWithPopup = vi.fn();
vi.mock("firebase/auth", () => ({
  reauthenticateWithPopup: (...args: unknown[]) => reauthenticateWithPopup(...args),
  signInWithPopup: vi.fn(),
}));
vi.mock("@/shared/lib/firebase", () => ({
  auth: { currentUser: { email: "a@b.c" }, signOut: vi.fn() },
  googleProvider: {},
}));

const USERS_ME_URL = "http://localhost:8000/v1/users/me";

function renderDialog(): void {
  render(
    <MemoryRouter>
      <DeleteAccountDialog isOpen onClose={vi.fn()} />
    </MemoryRouter>,
  );
}

const getDeleteButton = (): HTMLElement =>
  screen.getByRole("button", { name: "Delete my account" });

describe("DeleteAccountDialog", () => {
  beforeEach(() => {
    reauthenticateWithPopup.mockReset();
    useToastStore.setState({ queue: [] });
    useAuthStore.setState({
      accessToken: "token",
      isAuthenticated: true,
      isLoading: false,
      user: { user_id: "u1", display_name: "Eldrin", onboarding_completed: true },
    });
    server.use(http.post("*/v1/auth/logout", () => new HttpResponse(null, { status: 204 })));
  });

  it("keeps the delete button disabled until the phrase is typed", async () => {
    renderDialog();

    expect(getDeleteButton()).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Type DELETE/), "DELETE");

    expect(getDeleteButton()).toBeEnabled();
  });

  it("re-authenticates, requests deletion, signs out and toasts", async () => {
    reauthenticateWithPopup.mockResolvedValue({});
    const calls: string[] = [];
    server.use(
      http.delete(USERS_ME_URL, () => {
        calls.push("delete");
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderDialog();

    await userEvent.type(screen.getByLabelText(/Type DELETE/), "DELETE");
    await userEvent.click(getDeleteButton());

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
    expect(reauthenticateWithPopup).toHaveBeenCalledTimes(1);
    expect(calls).toEqual(["delete"]);
    expect(useToastStore.getState().queue[0]?.message).toMatch(/scheduled for deletion/);
  });

  it("leaves the account untouched when re-authentication fails", async () => {
    reauthenticateWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });
    const calls: string[] = [];
    server.use(
      http.delete(USERS_ME_URL, () => {
        calls.push("delete");
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderDialog();

    await userEvent.type(screen.getByLabelText(/Type DELETE/), "DELETE");
    await userEvent.click(getDeleteButton());

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't verify/i);
    expect(calls).toEqual([]);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("stays signed in and allows retry when the deletion request fails", async () => {
    reauthenticateWithPopup.mockResolvedValue({});
    server.use(http.delete(USERS_ME_URL, () => new HttpResponse(null, { status: 500 })));
    renderDialog();

    await userEvent.type(screen.getByLabelText(/Type DELETE/), "DELETE");
    await userEvent.click(getDeleteButton());

    expect(await screen.findByRole("alert")).toHaveTextContent(/not deleted/i);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(getDeleteButton()).toBeEnabled();
  });
});
