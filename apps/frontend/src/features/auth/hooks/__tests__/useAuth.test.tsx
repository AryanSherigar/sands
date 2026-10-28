import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { NON_ALPHA_CONFIG, alphaConfigHandler } from "@/test/alphaFixtures";
import { useToastStore } from "@/shared/stores/toast.store";
import { useAuthStore } from "../../stores/auth.store";
import {
  SIGN_IN_CANCELLED_MESSAGE,
  SIGN_IN_FAILED_MESSAGE,
} from "../../constants/auth-messages";
import { useAuth } from "../useAuth";

const signInWithPopup = vi.fn();
vi.mock("firebase/auth", () => ({
  signInWithPopup: (...args: unknown[]) => signInWithPopup(...args),
}));
vi.mock("@/shared/lib/firebase", () => ({
  auth: { currentUser: null, signOut: vi.fn() },
  googleProvider: {},
}));

const API_USER = { id: "u1", onboarding_completed: false };

const mockFirebaseSuccess = (): void => {
  signInWithPopup.mockResolvedValue({
    user: { getIdToken: () => Promise.resolve("firebase-token") },
  });
};

describe("useAuth.loginWithGoogle", () => {
  beforeEach(() => {
    signInWithPopup.mockReset();
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
  });

  it("returns true and stores the user on success", async () => {
    mockFirebaseSuccess();
    server.use(
      http.post("*/v1/auth/token", () =>
        HttpResponse.json({ access_token: "jwt", user: API_USER }),
      ),
    );
    const { result } = renderHook(() => useAuth());
    let isSignedIn = false;
    await act(async () => {
      isSignedIn = await result.current.loginWithGoogle();
    });
    expect(isSignedIn).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("shows a welcome-back toast when a pending deletion was cancelled", async () => {
    mockFirebaseSuccess();
    useToastStore.setState({ queue: [] });
    server.use(
      http.post("*/v1/auth/token", () =>
        HttpResponse.json({
          access_token: "jwt",
          user: API_USER,
          is_account_restored: true,
        }),
      ),
    );
    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.loginWithGoogle();
    });
    expect(useToastStore.getState().queue[0]?.message).toBe(
      "Welcome back, your account was restored.",
    );
  });

  it("reports a cancelled popup with the cancelled copy", async () => {
    signInWithPopup.mockRejectedValue({ code: "auth/popup-closed-by-user" });
    const { result } = renderHook(() => useAuth());
    let isSignedIn = true;
    await act(async () => {
      isSignedIn = await result.current.loginWithGoogle();
    });
    expect(isSignedIn).toBe(false);
    expect(result.current.error).toBe(SIGN_IN_CANCELLED_MESSAGE);
  });

  it("reports a failed token exchange with the failure copy", async () => {
    mockFirebaseSuccess();
    server.use(
      http.post("*/v1/auth/token", () => new HttpResponse(null, { status: 500 })),
    );
    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.loginWithGoogle();
    });
    expect(result.current.error).toBe(SIGN_IN_FAILED_MESSAGE);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
