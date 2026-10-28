import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { NarrativeTurnCallbacks } from "../lib/turn-stream";
import { useTurnStream } from "./useTurnStream";

let capturedCallbacks: NarrativeTurnCallbacks | null = null;
const cancelTurn = vi.fn();

vi.mock("../lib/turn-stream", () => ({
  startNarrativeTurn: (_request: unknown, callbacks: NarrativeTurnCallbacks) => {
    capturedCallbacks = callbacks;
    return cancelTurn;
  },
}));

const request = { playthroughId: "pt-1", participantId: "part-1", actionText: "Look around." };

describe("useTurnStream", () => {
  beforeEach(() => {
    capturedCallbacks = null;
    cancelTurn.mockClear();
  });

  it("streams narration while a turn is running and reports the finished turn", () => {
    const onTurnComplete = vi.fn();
    const { result } = renderHook(() => useTurnStream({ onTurnComplete }));

    act(() => result.current.submitTurn(request));
    expect(result.current.isStreaming).toBe(true);

    act(() => capturedCallbacks!.onNarration("It is "));
    act(() => capturedCallbacks!.onNarration("dark."));
    expect(result.current.narration).toBe("It is dark.");

    act(() => capturedCallbacks!.onDone());
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.narration).toBe("");
    expect(onTurnComplete).toHaveBeenCalledWith({
      actionText: "Look around.",
      narration: "It is dark.",
    });
  });

  it("keeps a failure message until the next turn starts", () => {
    const { result } = renderHook(() => useTurnStream({ onTurnComplete: vi.fn() }));

    act(() => result.current.submitTurn(request));
    act(() => capturedCallbacks!.onFailure("Connection lost."));
    expect(result.current.failureMessage).toBe("Connection lost.");
    expect(result.current.isStreaming).toBe(false);

    act(() => result.current.submitTurn(request));
    expect(result.current.failureMessage).toBeNull();
  });

  it("ignores a second submit while a turn is already streaming", () => {
    const { result } = renderHook(() => useTurnStream({ onTurnComplete: vi.fn() }));

    act(() => result.current.submitTurn(request));
    const firstCallbacks = capturedCallbacks;
    act(() => result.current.submitTurn(request));

    expect(capturedCallbacks).toBe(firstCallbacks);
  });

  it("cancels the running turn on unmount and on cancelTurn", () => {
    const { result, unmount } = renderHook(() => useTurnStream({ onTurnComplete: vi.fn() }));
    act(() => result.current.submitTurn(request));

    act(() => result.current.cancelTurn());
    expect(cancelTurn).toHaveBeenCalledTimes(1);
    expect(result.current.isStreaming).toBe(false);

    act(() => result.current.submitTurn(request));
    unmount();
    expect(cancelTurn).toHaveBeenCalledTimes(2);
  });

  it("collects notices", () => {
    const { result } = renderHook(() => useTurnStream({ onTurnComplete: vi.fn() }));
    act(() => result.current.submitTurn(request));
    act(() => capturedCallbacks!.onNotice("No scene art today."));
    expect(result.current.notice).toBe("No scene art today.");
  });
});
