import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";
import { NarrationPlaybackController } from "../narration-playback";

describe("NarrationPlaybackController", () => {
  let controller: NarrationPlaybackController;
  let playSpy: MockInstance;
  let pauseSpy: MockInstance;

  beforeEach(() => {
    controller = new NarrationPlaybackController();
    playSpy = vi
      .spyOn(HTMLMediaElement.prototype, "play")
      .mockReturnValue(Promise.resolve());
    pauseSpy = vi
      .spyOn(HTMLMediaElement.prototype, "pause")
      .mockImplementation(() => {});
  });

  afterEach(() => {
    playSpy.mockRestore();
    pauseSpy.mockRestore();
  });

  it("starts with nothing playing", () => {
    expect(controller.getPlayingTurnId()).toBeNull();
  });

  it("plays a turn's audio and tracks it as the playing turn", () => {
    controller.play("turn-1", "https://example.com/turn-1.wav");

    expect(controller.getPlayingTurnId()).toBe("turn-1");
    expect(playSpy).toHaveBeenCalledTimes(1);
  });

  it("stops any currently playing clip before starting a new one", () => {
    controller.play("turn-1", "https://example.com/turn-1.wav");
    controller.play("turn-2", "https://example.com/turn-2.wav");

    expect(controller.getPlayingTurnId()).toBe("turn-2");
    expect(pauseSpy).toHaveBeenCalledTimes(1);
  });

  it("stop() clears the playing turn", () => {
    controller.play("turn-1", "https://example.com/turn-1.wav");
    controller.stop();

    expect(controller.getPlayingTurnId()).toBeNull();
    expect(pauseSpy).toHaveBeenCalledTimes(1);
  });

  it("stop() is a no-op when nothing is playing", () => {
    controller.stop();

    expect(pauseSpy).not.toHaveBeenCalled();
  });

  it("notifies listeners on play and stop", () => {
    const listener = vi.fn();
    const unsubscribe = controller.onPlaybackChange(listener);

    controller.play("turn-1", "https://example.com/turn-1.wav");
    controller.stop();
    unsubscribe();
    controller.play("turn-2", "https://example.com/turn-2.wav");

    expect(listener).toHaveBeenCalledTimes(2);
    expect(listener).toHaveBeenNthCalledWith(1, "turn-1");
    expect(listener).toHaveBeenNthCalledWith(2, null);
  });

  it("clears the playing turn when playback ends naturally", () => {
    controller.play("turn-1", "https://example.com/turn-1.wav");
    const audio = (controller as unknown as { audio: HTMLAudioElement }).audio;

    audio.onended?.(new Event("ended"));

    expect(controller.getPlayingTurnId()).toBeNull();
  });
});
