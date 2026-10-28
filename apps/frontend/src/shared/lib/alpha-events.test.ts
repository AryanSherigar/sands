import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import {
  emitAlphaEvent,
  flushAlphaEvents,
  flushAlphaEventsOnHide,
  resetAlphaEventsForTests,
  setAlphaCollectionEnabled,
} from "./alpha-events";
import {
  ALPHA_EVENTS_FLUSH_INTERVAL_MS,
  ALPHA_EVENTS_MAX_BATCH,
} from "@/shared/constants/alpha-events";

interface ReceivedBatch {
  session_id: string;
  events: Array<{ name: string; props: Record<string, unknown> }>;
}

const SESSION_PROPS = {
  visible_ms: 0,
  hidden_ms: 0,
  sfx_played_count: 0,
  audio_blocked_count: 0,
};

function captureBatches(): ReceivedBatch[] {
  const batches: ReceivedBatch[] = [];
  server.use(
    http.post("*/v1/alpha/events", async ({ request }) => {
      batches.push((await request.json()) as ReceivedBatch);
      return HttpResponse.json({ accepted: 1 }, { status: 202 });
    }),
  );
  return batches;
}

describe("alpha-events", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    resetAlphaEventsForTests();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("records nothing until collection is enabled", async () => {
    const batches = captureBatches();

    emitAlphaEvent("session_start", SESSION_PROPS);
    await flushAlphaEvents();

    expect(batches).toEqual([]);
  });

  it("batches events and sends them on the interval", async () => {
    const batches = captureBatches();
    setAlphaCollectionEnabled(true);

    emitAlphaEvent("session_start", SESSION_PROPS);
    emitAlphaEvent("audio_blocked", { reason: "muted" });
    expect(batches).toEqual([]);
    await vi.advanceTimersByTimeAsync(ALPHA_EVENTS_FLUSH_INTERVAL_MS);
    await vi.waitFor(() => expect(batches).toHaveLength(1));

    expect(batches[0].events.map((event) => event.name)).toEqual([
      "session_start",
      "audio_blocked",
    ]);
    expect(batches[0].session_id).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("sends at once when a full batch is queued", async () => {
    const batches = captureBatches();
    setAlphaCollectionEnabled(true);

    for (let i = 0; i < ALPHA_EVENTS_MAX_BATCH; i += 1) {
      emitAlphaEvent("audio_blocked", { reason: "error" });
    }
    await vi.waitFor(() => expect(batches).toHaveLength(1));

    expect(batches[0].events).toHaveLength(ALPHA_EVENTS_MAX_BATCH);
  });

  it("drops the batch with one warning when the endpoint fails, without retrying", async () => {
    let requests = 0;
    server.use(
      http.post("*/v1/alpha/events", () => {
        requests += 1;
        return HttpResponse.json({ detail: "down" }, { status: 500 });
      }),
    );
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    setAlphaCollectionEnabled(true);

    emitAlphaEvent("audio_blocked", { reason: "error" });
    await flushAlphaEvents();
    emitAlphaEvent("audio_blocked", { reason: "error" });
    await flushAlphaEvents();

    expect(requests).toBe(2);
    expect(warn).toHaveBeenCalledTimes(1);
  });

  it("never throws, even when the network is unreachable", async () => {
    server.use(http.post("*/v1/alpha/events", () => HttpResponse.error()));
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    setAlphaCollectionEnabled(true);

    emitAlphaEvent("audio_blocked", { reason: "error" });

    await expect(flushAlphaEvents()).resolves.toBeUndefined();
  });

  it("flushes with a keepalive request when the page is hidden", () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 202 }));
    setAlphaCollectionEnabled(true);

    emitAlphaEvent("audio_blocked", { reason: "autoplay_policy" });
    flushAlphaEventsOnHide();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/v1/alpha/events");
    expect(init?.keepalive).toBe(true);
  });

  it("forgets queued events when collection is switched off", async () => {
    const batches = captureBatches();
    setAlphaCollectionEnabled(true);
    emitAlphaEvent("audio_blocked", { reason: "error" });

    setAlphaCollectionEnabled(false);
    await flushAlphaEvents();

    expect(batches).toEqual([]);
  });
});
