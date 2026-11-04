import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SSEHandlers } from "./sse-client";
import { startNarrativeTurn, type NarrativeTurnCallbacks } from "./turn-stream";
import { RateLimitError } from "./rate-limit-error";

let capturedUrl = "";
let capturedBody: Record<string, unknown> = {};
let capturedHandlers: SSEHandlers | null = null;
const cancelConnection = vi.fn();

vi.mock("./sse-client", () => ({
  createPostSSEConnection: (
    url: string,
    body: Record<string, unknown>,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    capturedUrl = url;
    capturedBody = body;
    capturedHandlers = handlers;
    return cancelConnection;
  },
}));

const buildCallbacks = (): NarrativeTurnCallbacks => ({
  onNarration: vi.fn(),
  onDone: vi.fn(),
  onFailure: vi.fn(),
  onNotice: vi.fn(),
});

const request = {
  playthroughId: "pt-1",
  participantId: "part-1",
  actionText: "I open the door.",
};

describe("startNarrativeTurn", () => {
  beforeEach(() => {
    capturedHandlers = null;
    cancelConnection.mockClear();
  });

  it("posts a narrative turn body to the turn endpoint", () => {
    startNarrativeTurn(request, buildCallbacks());

    expect(capturedUrl).toMatch(/\/v1\/turn$/);
    expect(capturedBody).toMatchObject({
      playthrough_id: "pt-1",
      participant_id: "part-1",
      action_text: "I open the door.",
      action_kind: "narrative",
      action_mode: "do",
      voice_output_requested: false,
    });
    expect(typeof capturedBody.client_action_id).toBe("string");
  });

  it("forwards narration chunks and finishes on done", () => {
    const callbacks = buildCallbacks();
    startNarrativeTurn(request, callbacks);

    capturedHandlers!.onEvent("narration", "The door ");
    capturedHandlers!.onEvent("narration", "creaks.");
    capturedHandlers!.onEvent("done", "{}");

    expect(callbacks.onNarration).toHaveBeenNthCalledWith(1, "The door ");
    expect(callbacks.onNarration).toHaveBeenNthCalledWith(2, "creaks.");
    expect(callbacks.onDone).toHaveBeenCalledTimes(1);
    expect(callbacks.onFailure).not.toHaveBeenCalled();
  });

  it("reports a degraded turn as a failure with the server message", () => {
    const callbacks = buildCallbacks();
    startNarrativeTurn(request, callbacks);

    capturedHandlers!.onEvent("degraded", "The narrator is resting.");

    expect(callbacks.onFailure).toHaveBeenCalledWith("The narrator is resting.");
  });

  it("surfaces quota and truncation notices without ending the turn", () => {
    const callbacks = buildCallbacks();
    startNarrativeTurn(request, callbacks);

    capturedHandlers!.onEvent("quota_notice", JSON.stringify({ detail: "No scene art today." }));
    capturedHandlers!.onEvent("input_truncated", JSON.stringify({ max_length: 500 }));

    expect(callbacks.onNotice).toHaveBeenCalledWith("No scene art today.");
    expect(callbacks.onNotice).toHaveBeenCalledWith(
      "Your action was too long, so only the first 500 characters were used.",
    );
    expect(callbacks.onDone).not.toHaveBeenCalled();
  });

  it("fails once when the connection closes without a terminal event", () => {
    const callbacks = buildCallbacks();
    startNarrativeTurn(request, callbacks);

    capturedHandlers!.onClose?.();
    capturedHandlers!.onClose?.();

    expect(callbacks.onFailure).toHaveBeenCalledTimes(1);
  });

  it("does not report a failure after done when the connection then closes", () => {
    const callbacks = buildCallbacks();
    startNarrativeTurn(request, callbacks);

    capturedHandlers!.onEvent("done", "{}");
    capturedHandlers!.onClose?.();

    expect(callbacks.onFailure).not.toHaveBeenCalled();
  });

  it("uses a rate limit error's own message and a generic one otherwise", () => {
    const limited = buildCallbacks();
    const limit = new RateLimitError(
      { detail: "Daily limit reached", code: "quota_exceeded", scope: "turn", reset_at: null },
      null,
    );
    startNarrativeTurn(request, limited);
    capturedHandlers!.onError?.(limit);
    expect(limited.onFailure).toHaveBeenCalledWith(limit.message);

    const dropped = buildCallbacks();
    startNarrativeTurn(request, dropped);
    capturedHandlers!.onError?.(new Error("network"));
    expect(dropped.onFailure).toHaveBeenCalledWith(
      "Connection lost. Your turn may not have saved. You can try again.",
    );
  });

  it("returns a cancel function that closes the connection", () => {
    const cancel = startNarrativeTurn(request, buildCallbacks());
    cancel();
    expect(cancelConnection).toHaveBeenCalledTimes(1);
  });
});
