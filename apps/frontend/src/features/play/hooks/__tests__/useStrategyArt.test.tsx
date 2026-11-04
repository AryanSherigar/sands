import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useStrategyArt } from "../useStrategyArt";

const PLAYTHROUGH_ID = "pt-1";
const ART_URL = "https://cdn.test/strategy-art/one.webp";
const ART_PATH = `*/trs/v1/strategy/playthroughs/${PLAYTHROUGH_ID}/art`;

const view = (status: string, artUrl: string | null) => ({
  kind: "event",
  item_id: "evt_1",
  status,
  art_url: artUrl,
  error_code: null,
  is_retryable: false,
});

describe("useStrategyArt", () => {
  it("returns the saved url after one request", async () => {
    const handler = vi.fn(() => HttpResponse.json(view("completed", ART_URL)));
    server.use(http.post(ART_PATH, handler));
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1"),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(result.current.artUrl).toBe(ART_URL));
    expect(result.current.isLoading).toBe(false);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("keeps loading while the server answers 409 and resolves on the next try", async () => {
    let calls = 0;
    server.use(
      http.post(ART_PATH, () => {
        calls += 1;
        if (calls === 1) return HttpResponse.json({ detail: "busy" }, { status: 409 });
        return HttpResponse.json(view("completed", ART_URL));
      }),
    );
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1", 300),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(calls).toBe(1));
    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.artUrl).toBe(ART_URL));
    expect(calls).toBe(2);
  });

  it("gives no art and does not retry when generation failed", async () => {
    const handler = vi.fn(() => HttpResponse.json(view("failed", null)));
    server.use(http.post(ART_PATH, handler));
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1", 20),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(result.current.artUrl).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("reports a request failure and retries on demand", async () => {
    let calls = 0;
    server.use(
      http.post(ART_PATH, () => {
        calls += 1;
        if (calls === 1) return HttpResponse.json({ detail: "boom" }, { status: 500 });
        return HttpResponse.json(view("completed", ART_URL));
      }),
    );
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1"),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(result.current.hasFailed).toBe(true));
    expect(result.current.isLoading).toBe(false);

    result.current.retry();

    await waitFor(() => expect(result.current.artUrl).toBe(ART_URL));
    expect(result.current.hasFailed).toBe(false);
  });

  it("marks a non-retryable generation failure as failed without a retry option", async () => {
    server.use(http.post(ART_PATH, () => HttpResponse.json(view("failed", null))));
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1"),
      { wrapper: createQueryWrapper() },
    );
    await waitFor(() => expect(result.current.hasFailed).toBe(true));
    expect(result.current.canRetry).toBe(false);
  });

  it("does not request without an item id", async () => {
    const handler = vi.fn(() => HttpResponse.json(view("completed", ART_URL)));
    server.use(http.post(ART_PATH, handler));
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", undefined),
      { wrapper: createQueryWrapper() },
    );
    expect(result.current.isLoading).toBe(false);
    expect(handler).not.toHaveBeenCalled();
  });

  it("stops offering a retry when the item is gone from the world", async () => {
    server.use(http.post(ART_PATH, () => HttpResponse.json({ detail: "Art item not found" }, { status: 404 })));
    const { result } = renderHook(
      () => useStrategyArt(PLAYTHROUGH_ID, "event", "evt_1", 20),
      { wrapper: createQueryWrapper() },
    );

    await waitFor(() => expect(result.current.hasFailed).toBe(true));
    expect(result.current.canRetry).toBe(false);
    expect(result.current.artUrl).toBeNull();
  });
});
