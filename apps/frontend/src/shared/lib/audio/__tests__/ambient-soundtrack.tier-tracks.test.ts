import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AmbientSoundtrackController } from "../ambient-soundtrack";
import { FakeAudioContext } from "./fakeAudioContext";

class StubAudio extends EventTarget {
  static instances: StubAudio[] = [];
  loop = false;
  preload = "";
  crossOrigin = "";
  src = "";
  constructor() {
    super();
    StubAudio.instances.push(this);
  }
  play(): Promise<void> {
    return Promise.resolve();
  }
  pause(): void {}
}

const TENSE = "https://tracks.test/tense.mp3";
const DREAD = "https://tracks.test/dread.mp3";
const MOOD_DEFAULT = "https://tracks.test/default-tension.mp3";

const playingElement = (): StubAudio | undefined =>
  StubAudio.instances.find((audio) => audio.src !== "");

describe("tier tracks in the ambient controller", () => {
  let controller: AmbientSoundtrackController;

  beforeEach(() => {
    StubAudio.instances = [];
    FakeAudioContext.instances = [];
    vi.stubGlobal("AudioContext", FakeAudioContext);
    Object.defineProperty(window, "AudioContext", {
      value: FakeAudioContext,
      configurable: true,
      writable: true,
    });
    vi.stubGlobal("Audio", StubAudio);
    controller = new AmbientSoundtrackController({ sfxFileLoader: async () => null });
    controller.init();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("switches track inside one mood when the URL differs", () => {
    expect(controller.transitionTo("tension", TENSE, { isForce: true })).toBe(true);

    expect(controller.transitionTo("tension", DREAD, { isForce: true })).toBe(true);
    expect(controller.getCurrentTrackUrl()).toBe(DREAD);
  });

  it("ignores the same mood with the same URL", () => {
    controller.transitionTo("tension", TENSE, { isForce: true });

    expect(controller.transitionTo("tension", TENSE, { isForce: true })).toBe(false);
  });

  it("plays the fallback when the tier track fails to load", () => {
    controller.transitionTo("tension", TENSE, {
      isForce: true,
      fallbackUrl: MOOD_DEFAULT,
    });
    const element = playingElement();

    element?.dispatchEvent(new Event("error"));

    expect(element?.src).toBe(MOOD_DEFAULT);
    expect(controller.getCurrentTrackUrl()).toBe(MOOD_DEFAULT);
  });

  it("ignores a load error from a track that was already replaced", () => {
    controller.transitionTo("tension", TENSE, {
      isForce: true,
      fallbackUrl: MOOD_DEFAULT,
    });
    const staleElement = playingElement();
    controller.transitionTo("tension", DREAD, { isForce: true });

    staleElement?.dispatchEvent(new Event("error"));

    expect(controller.getCurrentTrackUrl()).toBe(DREAD);
  });

  it("does not loop on a failing fallback", () => {
    controller.transitionTo("tension", MOOD_DEFAULT, {
      isForce: true,
      fallbackUrl: MOOD_DEFAULT,
    });
    const element = playingElement();

    element?.dispatchEvent(new Event("error"));

    expect(element?.src).toBe(MOOD_DEFAULT);
  });
});
