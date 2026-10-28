import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { server } from "@/test/msw/server";
import { MemoryRetryError, retryMemory } from "../memory.api";

const refreshAuthTokenMock = vi.hoisted(() => vi.fn());

vi.mock("@/shared/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/lib/api-client")>()),
  refreshAuthToken: refreshAuthTokenMock,
}));

const PLAYTHROUGH_ID = "playthrough-1";
const RETRY_URL = `*/v1/playthroughs/${PLAYTHROUGH_ID}/memory/retry`;
const EXPIRED_TOKEN = "expired-token";
const FRESH_TOKEN = "fresh-token";

describe("retryMemory", () => {
  beforeEach(() => {
    refreshAuthTokenMock.mockReset();
    useAuthStore.setState({ accessToken: EXPIRED_TOKEN });
  });

  it("returns the degraded reasons on success without refreshing", async () => {
    server.use(
      http.post(RETRY_URL, () =>
        HttpResponse.json({ degraded_reasons: ["retrieval_failed"] }),
      ),
    );

    const result = await retryMemory(PLAYTHROUGH_ID);

    expect(result.degraded_reasons).toEqual(["retrieval_failed"]);
    expect(refreshAuthTokenMock).not.toHaveBeenCalled();
  });

  it("refreshes an expired token once and retries with the new one", async () => {
    refreshAuthTokenMock.mockResolvedValue(FRESH_TOKEN);
    const seenAuthorization: (string | null)[] = [];
    server.use(
      http.post(RETRY_URL, ({ request }) => {
        const authorization = request.headers.get("Authorization");
        seenAuthorization.push(authorization);
        if (authorization === `Bearer ${FRESH_TOKEN}`) {
          return HttpResponse.json({ degraded_reasons: [] });
        }
        return new HttpResponse(null, { status: 401 });
      }),
    );

    const result = await retryMemory(PLAYTHROUGH_ID);

    expect(result.degraded_reasons).toEqual([]);
    expect(refreshAuthTokenMock).toHaveBeenCalledTimes(1);
    expect(seenAuthorization).toEqual([
      `Bearer ${EXPIRED_TOKEN}`,
      `Bearer ${FRESH_TOKEN}`,
    ]);
  });

  it("fails with a memory error when the refresh yields no token", async () => {
    refreshAuthTokenMock.mockResolvedValue(null);
    server.use(
      http.post(RETRY_URL, () => new HttpResponse(null, { status: 401 })),
    );

    await expect(retryMemory(PLAYTHROUGH_ID)).rejects.toBeInstanceOf(
      MemoryRetryError,
    );
  });
});
