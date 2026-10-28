import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createGetSSEConnection,
  createPostSSEConnection,
  SSEHandlers,
} from "./sse-client";
import { refreshAuthToken } from "./api-client";
import { AlphaPausedError } from "./alpha-paused-error";
import { RateLimitError } from "./rate-limit-error";

vi.mock("./api-client", () => ({
  refreshAuthToken: vi.fn(),
}));

function createMockStream(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

describe("sse-client", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("parses events and ignores keepalive ping comments", async () => {
    const stream = createMockStream([
      ": ping - 2026-10-27T14:15:38Z\r\n\r\n",
      "event: narration\r\ndata: The cave is dark.\r\n\r\n",
      ": ping - 2026-10-27T14:15:53Z\r\n\r\n",
      "event: done\r\ndata: \r\n\r\n",
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: stream,
      }),
    );

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const handlers: SSEHandlers = {
      onEvent: (event, data) => receivedEvents.push({ event, data }),
    };

    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/session/1/spectate",
      null,
      handlers,
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(receivedEvents).toEqual([
      { event: "narration", data: "The cave is dark." },
      { event: "done", data: "" },
    ]);

    cleanup();
  });

  it("reconnects with backoff when a GET stream terminates unexpectedly", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        body: createMockStream(["event: msg\ndata: first\n\n"]),
      })
      .mockResolvedValueOnce({
        ok: true,
        body: createMockStream(["event: msg\ndata: second\n\n"]),
      });

    vi.stubGlobal("fetch", fetchMock);

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const handlers: SSEHandlers = {
      onEvent: (event, data) => receivedEvents.push({ event, data }),
    };

    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/session/1/spectate",
      null,
      handlers,
      undefined,
      { initialDelayMs: 500, maxDelayMs: 2000, backoffMultiplier: 2 },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(receivedEvents).toHaveLength(1);

    // Advance timer past initial retry delay
    await vi.advanceTimersByTimeAsync(500);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(receivedEvents).toHaveLength(2);
    expect(receivedEvents[1].data).toBe("second");

    cleanup();
  });

  it("stops reconnecting when cleanup is called", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: createMockStream(["event: msg\ndata: one\n\n"]),
    });
    vi.stubGlobal("fetch", fetchMock);

    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/session/1/spectate",
      null,
      { onEvent: vi.fn() },
      undefined,
      { initialDelayMs: 500 },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Abort before retry timer fires
    cleanup();
    await vi.advanceTimersByTimeAsync(1000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not auto-reconnect for POST connections", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: createMockStream(["event: done\ndata: \n\n"]),
    });
    vi.stubGlobal("fetch", fetchMock);

    const cleanup = createPostSSEConnection(
      "http://localhost:8001/v1/turn",
      { action: "look" },
      null,
      { onEvent: vi.fn() },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(5000);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    cleanup();
  });

  it("preserves leading indentation and trailing spaces on data lines per SSE spec", async () => {
    const stream = createMockStream([
      "event: token\ndata:   indented text with trailing   \n\n",
      "event: done\ndata: \n\n",
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: stream,
      }),
    );

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/stream",
      null,
      { onEvent: (event, data) => receivedEvents.push({ event, data }) },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(receivedEvents).toEqual([
      { event: "token", data: "  indented text with trailing   " },
      { event: "done", data: "" },
    ]);

    cleanup();
  });

  it("correctly handles CRLF line endings split across chunk boundaries", async () => {
    const stream = createMockStream([
      "event: narration\r\ndata: Split chunk\r",
      "\n\r\nevent: done\r\ndata: \r\n\r\n",
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: stream,
      }),
    );

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/stream",
      null,
      { onEvent: (event, data) => receivedEvents.push({ event, data }) },
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(receivedEvents).toEqual([
      { event: "narration", data: "Split chunk" },
      { event: "done", data: "" },
    ]);

    cleanup();
  });

  it("refreshes the token and retries once on a 401", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 })
      .mockResolvedValueOnce({
        ok: true,
        body: createMockStream(["event: msg\ndata: recovered\n\n"]),
      });
    vi.stubGlobal("fetch", fetchMock);
    vi.mocked(refreshAuthToken).mockResolvedValue("new-token");

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/session/1/spectate",
      "expired-token",
      { onEvent: (event, data) => receivedEvents.push({ event, data }) },
    );

    await vi.advanceTimersByTimeAsync(0);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1]?.headers?.Authorization).toBe(
      "Bearer new-token",
    );
    expect(receivedEvents).toEqual([{ event: "msg", data: "recovered" }]);

    cleanup();
  });

  it("surfaces an error without retrying when the refresh fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 401 });
    vi.stubGlobal("fetch", fetchMock);
    vi.mocked(refreshAuthToken).mockResolvedValue(null);

    const onError = vi.fn();
    const cleanup = createGetSSEConnection(
      "http://localhost:8001/v1/session/1/spectate",
      "expired-token",
      { onEvent: vi.fn(), onError },
      undefined,
      { initialDelayMs: 500 },
    );

    await vi.advanceTimersByTimeAsync(0);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledTimes(1);

    cleanup();
  });

  it("reports a 429 as a typed RateLimitError without opening the stream", async () => {
    const body = {
      detail: "You've reached today's turn limit. It resets at 00:00 UTC.",
      code: "quota_exceeded",
      scope: "turn",
      reset_at: "2026-10-27T00:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      body: null,
      headers: new Headers({ "Retry-After": "120" }),
      json: () => Promise.resolve(body),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onError = vi.fn();
    const onOpen = vi.fn();

    createPostSSEConnection(
      "http://localhost:8001/v1/turn",
      {},
      null,
      { onEvent: vi.fn(), onError, onOpen },
    );
    await vi.runAllTimersAsync();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onOpen).not.toHaveBeenCalled();
    const error = onError.mock.calls[0][0];
    expect(error).toBeInstanceOf(RateLimitError);
    expect(error.message).toBe(body.detail);
    expect(error.retryAfterSeconds).toBe(120);
  });

  it("reports a 503 alpha_paused as a typed AlphaPausedError", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      body: null,
      headers: new Headers(),
      json: () =>
        Promise.resolve({ detail: "closed", code: "alpha_paused" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onError = vi.fn();

    createPostSSEConnection("http://localhost:8001/v1/turn", {}, null, {
      onEvent: vi.fn(),
      onError,
    });
    await vi.runAllTimersAsync();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(AlphaPausedError);
  });

  it("still reports a quota 503 as a RateLimitError", async () => {
    const body = {
      detail: "Temporarily unavailable.",
      code: "quota_unavailable",
      scope: "turn",
      reset_at: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        body: null,
        headers: new Headers(),
        json: () => Promise.resolve(body),
      }),
    );
    const onError = vi.fn();

    createPostSSEConnection("http://localhost:8001/v1/turn", {}, null, {
      onEvent: vi.fn(),
      onError,
    });
    await vi.runAllTimersAsync();

    expect(onError.mock.calls[0][0]).toBeInstanceOf(RateLimitError);
  });
});
