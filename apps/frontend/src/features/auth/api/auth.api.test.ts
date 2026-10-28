import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { refreshAccessToken } from "./auth.api";

const REFRESH_URL = "http://localhost:8000/v1/auth/refresh";

describe("refreshAccessToken", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("retries once and succeeds when another tab already rotated the refresh cookie", async () => {
    let callCount = 0;
    server.use(
      http.post(REFRESH_URL, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: "Refresh token already used or rotated" },
            { status: 401 },
          );
        }
        return HttpResponse.json({
          access_token: "new-access-token",
          token_type: "bearer",
          expires_in: 900,
          user: { user_id: "u1", display_name: "Test User" },
        });
      }),
    );

    const resultPromise = refreshAccessToken();
    await vi.advanceTimersByTimeAsync(300);
    const result = await resultPromise;

    expect(callCount).toBe(2);
    expect(result.access_token).toBe("new-access-token");
  });

  it("does not retry on a non-stale-token 401", async () => {
    let callCount = 0;
    server.use(
      http.post(REFRESH_URL, () => {
        callCount += 1;
        return HttpResponse.json(
          { detail: "Invalid or expired refresh token" },
          { status: 401 },
        );
      }),
    );

    await expect(refreshAccessToken()).rejects.toBeTruthy();
    expect(callCount).toBe(1);
  });

  it("single-flights concurrent callers within the same tab onto one request", async () => {
    let callCount = 0;
    server.use(
      http.post(REFRESH_URL, () => {
        callCount += 1;
        return HttpResponse.json({
          access_token: "shared-token",
          token_type: "bearer",
          expires_in: 900,
          user: { user_id: "u1", display_name: "Test User" },
        });
      }),
    );

    const [first, second] = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    expect(callCount).toBe(1);
    expect(first.access_token).toBe("shared-token");
    expect(second.access_token).toBe("shared-token");
  });
});
