import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SceneMessageCallbacks } from "../../lib/scene-stream";
import { useLetterSceneStream } from "../useLetterSceneStream";

const streamMock = vi.hoisted(() => ({
  start: vi.fn(),
  callbacks: null as SceneMessageCallbacks | null,
  cancel: vi.fn(),
}));

vi.mock("../../lib/scene-stream", () => ({
  startSceneMessage: (
    sceneId: string,
    text: string,
    callbacks: SceneMessageCallbacks,
    options: unknown,
  ) => {
    streamMock.callbacks = callbacks;
    streamMock.start(sceneId, text, options);
    return streamMock.cancel;
  },
}));

const refresh = vi.fn(() => Promise.resolve());

function setup(sceneId: string | null = "scene-1") {
  return renderHook(() => useLetterSceneStream(sceneId, refresh));
}

describe("useLetterSceneStream", () => {
  beforeEach(() => {
    streamMock.start.mockClear();
    streamMock.cancel.mockClear();
    streamMock.callbacks = null;
    refresh.mockClear();
  });

  it("opens the letter with the open kind, streams it, and refreshes when done", async () => {
    const { result } = setup();
    let opened: Promise<string> | undefined;
    act(() => {
      opened = result.current.openLetter();
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "", { kind: "open" });
    expect(result.current.isStreaming).toBe(true);

    act(() => streamMock.callbacks?.onNarration("Valdren, "));
    act(() => streamMock.callbacks?.onNarration("the fords are watched."));
    expect(result.current.streamedText).toBe("Valdren, the fords are watched.");

    await act(async () => {
      streamMock.callbacks?.onDone();
      await expect(opened).resolves.toBe("Valdren, the fords are watched.");
    });
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(result.current.isStreaming).toBe(false);
  });

  it("asks the scribe with the instruction and current draft and resolves with the draft", async () => {
    const { result } = setup();
    let draft: Promise<string> | undefined;
    act(() => {
      draft = result.current.requestScribeDraft("Make it firmer", "Dear Mira");
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "Make it firmer", {
      kind: "scribe",
      currentDraft: "Dear Mira",
    });
    act(() => streamMock.callbacks?.onNarration("Dear Mira, we hold the fords."));
    act(() => streamMock.callbacks?.onDone());
    await expect(draft).resolves.toBe("Dear Mira, we hold the fords.");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("rejects the scribe request with the failure message when the stream degrades", async () => {
    const { result } = setup();
    let draft: Promise<string> | undefined;
    act(() => {
      draft = result.current.requestScribeDraft("Shorter", "Dear Mira");
    });
    const rejection = expect(draft).rejects.toThrow("The letter could not be written.");
    act(() => streamMock.callbacks?.onFailure("The letter could not be written."));
    await rejection;
    expect(result.current.failureMessage).toBe("The letter could not be written.");
  });

  it("seals the real prose and reports success after refreshing", async () => {
    const { result } = setup();
    let sealed: Promise<boolean> | undefined;
    act(() => {
      sealed = result.current.sealLetter("Our bailiffs will walk the line.");
    });
    expect(streamMock.start).toHaveBeenCalledWith(
      "scene-1",
      "Our bailiffs will walk the line.",
      { kind: "seal" },
    );
    act(() => streamMock.callbacks?.onDone());
    await expect(sealed).resolves.toBe(true);
    expect(refresh).toHaveBeenCalled();
  });

  it("reports a failed seal as false, keeps the failure message, and still refreshes", async () => {
    const { result } = setup();
    let sealed: Promise<boolean> | undefined;
    act(() => {
      sealed = result.current.sealLetter("Prose");
    });
    act(() => streamMock.callbacks?.onFailure("Connection lost."));
    await expect(sealed).resolves.toBe(false);
    expect(result.current.failureMessage).toBe("Connection lost.");
    expect(refresh).toHaveBeenCalled();
  });

  it("refuses a second action while one is streaming", async () => {
    const { result } = setup();
    act(() => {
      void result.current.openLetter();
    });
    await expect(result.current.sealLetter("Prose")).resolves.toBe(false);
    expect(streamMock.start).toHaveBeenCalledTimes(1);
  });

  it("does nothing without a scene", async () => {
    const { result } = setup(null);
    await expect(result.current.sealLetter("Prose")).resolves.toBe(false);
    expect(streamMock.start).not.toHaveBeenCalled();
  });

  it("cancels an in-flight stream on unmount", () => {
    const { result, unmount } = setup();
    act(() => {
      void result.current.openLetter();
    });
    unmount();
    expect(streamMock.cancel).toHaveBeenCalled();
  });
});
