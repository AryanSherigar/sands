import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import {
  ALPHA_CONFIG,
  NON_ALPHA_CONFIG,
} from "@/test/alphaFixtures";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { setAlphaCollectionEnabled } from "@/shared/lib/alpha-events";
import { useAlphaCollection } from "../useAlphaCollection";

vi.mock("@/shared/lib/alpha-events", () => ({
  setAlphaCollectionEnabled: vi.fn(),
}));

function consentIs(isCurrent: boolean): void {
  server.use(
    http.get("*/v1/users/me", () =>
      HttpResponse.json({ alpha_consent_is_current: isCurrent }),
    ),
  );
}

describe("useAlphaCollection", () => {
  beforeEach(() => {
    vi.mocked(setAlphaCollectionEnabled).mockClear();
    useAuthStore.setState({ isAuthenticated: true });
  });

  afterEach(() => {
    useAuthStore.setState({ isAuthenticated: false });
  });

  it("collects for a signed-in tester on the current consent", async () => {
    consentIs(true);

    const { result } = renderHook(() => useAlphaCollection(), {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await waitFor(() => expect(result.current).toBe(true));
    expect(setAlphaCollectionEnabled).toHaveBeenLastCalledWith(true);
  });

  it("does not collect when consent is not current", async () => {
    consentIs(false);

    const { result } = renderHook(() => useAlphaCollection(), {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await waitFor(() =>
      expect(setAlphaCollectionEnabled).toHaveBeenCalledWith(false),
    );
    expect(result.current).toBe(false);
  });

  it("does not collect outside alpha mode", () => {
    const { result } = renderHook(() => useAlphaCollection(), {
      wrapper: createQueryWrapper(NON_ALPHA_CONFIG),
    });

    expect(result.current).toBe(false);
  });

  it("does not collect for a signed-out visitor", () => {
    useAuthStore.setState({ isAuthenticated: false });

    const { result } = renderHook(() => useAlphaCollection(), {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    expect(result.current).toBe(false);
  });
});
