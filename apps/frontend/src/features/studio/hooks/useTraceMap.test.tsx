import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeLabelMapFromRows } from "@/shared/lib/map-tracing/testImages";
import type {
  TraceResult,
  TraceWorkerRequest,
  TraceWorkerResponse,
} from "@/shared/types/strategy-map.types";
import { useTraceMap } from "./useTraceMap";

const RESULT: TraceResult = {
  document: {
    schema_version: 1,
    source: "manual",
    width: 1,
    height: 1,
    image_url: null,
    regions: [],
    roads: [],
  },
  problems: [],
  pixelCounts: {},
};

class StubWorker {
  static reply: (request: TraceWorkerRequest) => TraceWorkerResponse = () => ({
    type: "done-map",
    result: RESULT,
  });
  static shouldCrash = false;
  onmessage: ((event: { data: TraceWorkerResponse }) => void) | null = null;
  onerror: (() => void) | null = null;
  postMessage(request: TraceWorkerRequest): void {
    if (StubWorker.shouldCrash) {
      queueMicrotask(() => this.onerror?.());
      return;
    }
    queueMicrotask(() => this.onmessage?.({ data: StubWorker.reply(request) }));
  }
  terminate(): void {}
}

const DEFAULT_REPLY = StubWorker.reply;

afterEach(() => {
  vi.unstubAllGlobals();
  StubWorker.reply = DEFAULT_REPLY;
  StubWorker.shouldCrash = false;
});

describe("useTraceMap", () => {
  it("resolves a retrace with the worker's result and toggles isTracing", async () => {
    vi.stubGlobal("Worker", StubWorker);
    const { result } = renderHook(() => useTraceMap());
    const map = makeLabelMapFromRows(["ab"]);
    let pending: Promise<TraceResult> | undefined;
    act(() => {
      pending = result.current.retrace(map, {}, { source: "manual", imageUrl: null });
    });
    expect(result.current.isTracing).toBe(true);
    await act(async () => {
      expect(await pending).toEqual(RESULT);
    });
    expect(result.current.isTracing).toBe(false);
  });

  it("rejects when the worker reports an error", async () => {
    StubWorker.reply = () => ({ type: "error", message: "boom" });
    vi.stubGlobal("Worker", StubWorker);
    const { result } = renderHook(() => useTraceMap());
    const map = makeLabelMapFromRows(["ab"]);
    await act(async () => {
      await expect(
        result.current.retrace(map, {}, { source: "manual", imageUrl: null }),
      ).rejects.toThrow("boom");
    });
    expect(result.current.isTracing).toBe(false);
  });

  it("rejects every waiting request when the worker crashes", async () => {
    StubWorker.shouldCrash = true;
    vi.stubGlobal("Worker", StubWorker);
    const { result } = renderHook(() => useTraceMap());
    const map = makeLabelMapFromRows(["ab"]);
    await act(async () => {
      await expect(
        result.current.retrace(map, {}, { source: "manual", imageUrl: null }),
      ).rejects.toThrow(/worker/i);
    });
    expect(result.current.isTracing).toBe(false);
  });
});
