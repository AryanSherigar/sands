import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SceneMessageCallbacks } from "../../lib/scene-stream";
import { useJudgmentSceneStream } from "../useJudgmentSceneStream";

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
  return renderHook(() => useJudgmentSceneStream(sceneId, refresh));
}

describe("useJudgmentSceneStream", () => {
  beforeEach(() => {
    streamMock.start.mockClear();
    streamMock.cancel.mockClear();
    streamMock.callbacks = null;
    refresh.mockClear();
  });

  it("opens the court with the open kind and returns the streamed tableau", async () => {
    const { result } = setup();
    let opened: Promise<string> | undefined;
    act(() => {
      opened = result.current.openCourt();
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "", { kind: "open" });
    act(() => streamMock.callbacks?.onNarration("The hall "));
    act(() => streamMock.callbacks?.onNarration("is silent."));
    expect(result.current.streamedText).toBe("The hall is silent.");
    act(() => streamMock.callbacks?.onDone());
    await expect(opened).resolves.toBe("The hall is silent.");
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(result.current.isStreaming).toBe(false);
  });

  it("speaks as a plain message and refreshes when done", async () => {
    const { result } = setup();
    let spoken: Promise<boolean> | undefined;
    act(() => {
      spoken = result.current.speak("Why did you rise?");
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "Why did you rise?", {});
    act(() => streamMock.callbacks?.onDone());
    await expect(spoken).resolves.toBe(true);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("pronounces with the verdict, nuance and decree text", async () => {
    const { result } = setup();
    let done: Promise<boolean> | undefined;
    act(() => {
      done = result.current.pronounce({
        verdict: "execute",
        nuance: "publicly",
        decreeText: "Let it be seen.",
      });
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "Let it be seen.", {
      kind: "pronounce",
      verdict: "execute",
      nuance: "publicly",
    });
    act(() => streamMock.callbacks?.onDone());
    await expect(done).resolves.toBe(true);
  });

  it("pronounces without a nuance when none is chosen", () => {
    const { result } = setup();
    act(() => {
      void result.current.pronounce({ verdict: "release", nuance: null, decreeText: "" });
    });
    expect(streamMock.start).toHaveBeenCalledWith("scene-1", "", {
      kind: "pronounce",
      verdict: "release",
    });
  });

  it("reports a failure message and does not refresh", async () => {
    const { result } = setup();
    let spoken: Promise<boolean> | undefined;
    act(() => {
      spoken = result.current.speak("Speak.");
    });
    act(() => streamMock.callbacks?.onFailure("The court could not be heard."));
    await expect(spoken).resolves.toBe(false);
    expect(result.current.failureMessage).toBe("The court could not be heard.");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("refuses to start a second stream while one is running", () => {
    const { result } = setup();
    act(() => {
      void result.current.speak("One.");
    });
    act(() => {
      void result.current.speak("Two.");
    });
    expect(streamMock.start).toHaveBeenCalledTimes(1);
  });

  it("cancels the stream on unmount", () => {
    const { result, unmount } = setup();
    act(() => {
      void result.current.speak("Speak.");
    });
    unmount();
    expect(streamMock.cancel).toHaveBeenCalled();
  });
});
