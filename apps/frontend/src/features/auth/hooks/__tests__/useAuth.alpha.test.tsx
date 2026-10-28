import { act, renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  ALPHA_CONSENT_VERSION,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { useAuthStore } from "../../stores/auth.store";
import {
  ALPHA_ERROR_MESSAGES,
  SIGN_IN_FAILED_MESSAGE,
} from "../../constants/auth-messages";
import {
  captureInviteFromUrl,
  clearInvite,
  readInvite,
} from "../../lib/inviteStorage";
import { useAuth } from "../useAuth";

const signInWithPopup = vi.fn();
vi.mock("firebase/auth", () => ({
  signInWithPopup: (...args: unknown[]) => signInWithPopup(...args),
}));
vi.mock("@/shared/lib/firebase", () => ({
  auth: { currentUser: null, signOut: vi.fn() },
  googleProvider: {},
}));

const API_USER = { user_id: "u1", display_name: "T", onboarding_completed: true };

const captureTokenBody = (): { body: Record<string, unknown> | null } => {
  const captured: { body: Record<string, unknown> | null } = { body: null };
  server.use(
    http.post("*/v1/auth/token", async ({ request }) => {
      captured.body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ access_token: "jwt", user: API_USER });
    }),
  );
  return captured;
};

const signIn = async (): Promise<{ isSignedIn: boolean; error: string | null }> => {
  const { result } = renderHook(() => useAuth());
  let isSignedIn = false;
  await act(async () => {
    isSignedIn = await result.current.loginWithGoogle();
  });
  return { isSignedIn, error: result.current.error };
};

describe("useAuth alpha sign-in", () => {
  beforeEach(() => {
    signInWithPopup.mockReset();
    signInWithPopup.mockResolvedValue({
      user: { getIdToken: () => Promise.resolve("firebase-token") },
    });
    clearInvite();
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
  });

  it("sends the captured invite and the consent version, then clears the invite", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    captureInviteFromUrl("?invite=link-code");
    const captured = captureTokenBody();

    const { isSignedIn } = await signIn();

    expect(isSignedIn).toBe(true);
    expect(captured.body).toEqual({
      firebase_id_token: "firebase-token",
      invite_code: "link-code",
      alpha_consent_version: ALPHA_CONSENT_VERSION,
    });
    expect(readInvite()).toBeNull();
  });

  it("sends neither field when alpha mode is off", async () => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    captureInviteFromUrl("?invite=link-code");
    const captured = captureTokenBody();

    await signIn();

    expect(captured.body).toEqual({ firebase_id_token: "firebase-token" });
  });

  it("still signs in when the config request fails", async () => {
    server.use(http.get("*/v1/alpha/config", () => new HttpResponse(null, { status: 500 })));
    const captured = captureTokenBody();

    const { isSignedIn } = await signIn();

    expect(isSignedIn).toBe(true);
    expect(captured.body).toEqual({ firebase_id_token: "firebase-token" });
  });

  it("keeps the invite when sign-in is refused so the tester can retry", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    captureInviteFromUrl("?invite=link-code");
    server.use(
      http.post("*/v1/auth/token", () =>
        HttpResponse.json({ detail: "x", code: "alpha_invite_invalid" }, { status: 403 }),
      ),
    );

    await signIn();

    expect(readInvite()).toBe("link-code");
  });

  it.each(Object.entries(ALPHA_ERROR_MESSAGES))(
    "shows the %s copy",
    async (code, message) => {
      server.use(alphaConfigHandler(ALPHA_CONFIG));
      server.use(
        http.post("*/v1/auth/token", () =>
          HttpResponse.json({ detail: "x", code }, { status: 403 }),
        ),
      );

      const { isSignedIn, error } = await signIn();

      expect(isSignedIn).toBe(false);
      expect(error).toBe(message);
      expect(error).not.toBe(SIGN_IN_FAILED_MESSAGE);
    },
  );

  it("uses the generic failure copy for an unrecognised 403 code", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    server.use(
      http.post("*/v1/auth/token", () =>
        HttpResponse.json({ detail: "x", code: "something_else" }, { status: 403 }),
      ),
    );

    const { error } = await signIn();

    expect(error).toBe(SIGN_IN_FAILED_MESSAGE);
  });
});
