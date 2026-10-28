import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  ALPHA_CONSENT_VERSION,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONSENT_COPY } from "@/features/auth/constants/alpha-consent";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import {
  SIGN_IN_CANCELLED_MESSAGE,
  SIGN_IN_FAILED_MESSAGE,
} from "@/features/auth/constants/auth-messages";
import {
  SIGN_IN_TRIGGER_COPY,
  type SignInTrigger,
} from "@/shared/constants/sign-in-triggers";
import { useSignInModalStore } from "@/shared/stores/signInModal.store";
import { SignInModal } from "../SignInModal";

const signInWithPopup = vi.fn();
vi.mock("firebase/auth", () => ({
  signInWithPopup: (...args: unknown[]) => signInWithPopup(...args),
}));
vi.mock("@/shared/lib/firebase", () => ({
  auth: { currentUser: null, signOut: vi.fn() },
  googleProvider: {},
}));

const openModal = (trigger: SignInTrigger): Promise<boolean> => {
  let pending: Promise<boolean> = Promise.resolve(false);
  act(() => {
    pending = useSignInModalStore.getState().open(trigger);
  });
  return pending;
};

describe("SignInModal", () => {
  beforeEach(() => {
    signInWithPopup.mockReset();
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    useSignInModalStore.setState({ trigger: null, resolvePending: null });
  });

  it("renders nothing until a trigger opens it", () => {
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the contextual title and benefit for the trigger", () => {
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    void openModal("save");
    expect(
      screen.getByRole("dialog", { name: SIGN_IN_TRIGGER_COPY.save.title }),
    ).toBeInTheDocument();
    expect(screen.getByText(SIGN_IN_TRIGGER_COPY.save.benefit)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms");
  });

  it("cannot be closed at the hard turn-limit gate", async () => {
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    void openModal("turn-limit");
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
  });

  it("resolves false when dismissed", async () => {
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    const pending = openModal("save");
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await expect(pending).resolves.toBe(false);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keeps the button active with cancelled copy when the popup is closed", async () => {
    signInWithPopup.mockRejectedValue({ code: "auth/popup-closed-by-user" });
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    void openModal("save");
    await userEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    expect(await screen.findByText(SIGN_IN_CANCELLED_MESSAGE)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeEnabled();
  });

  it("offers Retry when the token exchange fails", async () => {
    signInWithPopup.mockResolvedValue({
      user: { getIdToken: () => Promise.resolve("t") },
    });
    server.use(http.post("*/v1/auth/token", () => new HttpResponse(null, { status: 500 })));
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    void openModal("save");
    await userEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    expect(await screen.findByText(SIGN_IN_FAILED_MESSAGE)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("resolves true and closes after a successful sign-in", async () => {
    signInWithPopup.mockResolvedValue({
      user: { getIdToken: () => Promise.resolve("t") },
    });
    server.use(
      http.post("*/v1/auth/token", () =>
        HttpResponse.json({ access_token: "jwt", user: { id: "u1", onboarding_completed: false } }),
      ),
    );
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    const pending = openModal("save");
    await userEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    await expect(pending).resolves.toBe(true);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the alpha consent text before the Google button in alpha mode", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    render(<SignInModal />, { wrapper: createQueryWrapper() });
    void openModal("save");
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
