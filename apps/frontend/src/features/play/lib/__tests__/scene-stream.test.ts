import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SSEHandlers } from "@/shared/lib/sse-client";
import { startSceneMessage } from "../scene-stream";

const sseMock = vi.hoisted(() => ({
  create: vi.fn(),
  handlers: null as SSEHandlers | null,
}));

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    url: string,
    body: unknown,
    token: string | null,
    handlers: SSEHandlers,
  ) => {
    sseMock.handlers = handlers;
    sseMock.create(url, body, token);
    return vi.fn();
  },
}));

function start() {
  const callbacks = { onNarration: vi.fn(), onDone: vi.fn(), onFailure: vi.fn() };
  startSceneMessage("scene-1", "Hello", callbacks);
  return callbacks;
}

describe("startSceneMessage", () => {
  beforeEach(() => {
    sseMock.handlers = null;
    sseMock.create.mockClear();
  });

  it("posts the message to the scene stream on TRS", () => {
    start();
    const [url, body] = sseMock.create.mock.calls[0];
    expect(url).toMatch(/\/v1\/scenes\/scene-1\/messages$/);
    expect(body).toEqual({ text: "Hello" });
  });

  it("forwards narration chunks and finishes once on done", () => {
    const callbacks = start();
    sseMock.handlers?.onEvent("narration", "Eight ");
    sseMock.handlers?.onEvent("narration", "turns.");
    sseMock.handlers?.onEvent("proposal", "{}");
    sseMock.handlers?.onEvent("done", "{}");
    sseMock.handlers?.onClose?.();
    expect(callbacks.onNarration.mock.calls).toEqual([["Eight "], ["turns."]]);
    expect(callbacks.onDone).toHaveBeenCalledTimes(1);
    expect(callbacks.onFailure).not.toHaveBeenCalled();
  });

  it("reports a degraded event as a failure with its message", () => {
    const callbacks = start();
    sseMock.handlers?.onEvent("degraded", "The scene could not continue.");
    expect(callbacks.onFailure).toHaveBeenCalledWith("The scene could not continue.");
    expect(callbacks.onDone).not.toHaveBeenCalled();
  });

  it("treats a close before done as a stopped stream, once", () => {
    const callbacks = start();
    sseMock.handlers?.onClose?.();
    sseMock.handlers?.onError?.(new Error("late"));
    expect(callbacks.onFailure).toHaveBeenCalledTimes(1);
    expect(callbacks.onFailure.mock.calls[0][0]).toMatch(/stopped responding/i);
  });

  it("reports a network error as a lost connection", () => {
    const callbacks = start();
    sseMock.handlers?.onError?.(new Error("boom"));
    expect(callbacks.onFailure.mock.calls[0][0]).toMatch(/connection lost/i);
  });
});
