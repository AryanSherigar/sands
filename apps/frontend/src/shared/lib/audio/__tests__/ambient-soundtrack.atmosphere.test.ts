import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AmbientSoundtrackController } from "../ambient-soundtrack";
import {
  PHANTOM_MAX_GAIN,
  WHISPER_DELAY_SPAN_MS,
  WHISPER_MIN_DELAY_MS,
} from "../phantom-whispers";
import { FakeAudioContext } from "./fakeAudioContext";

const installFakeAudio = (): void => {
  FakeAudioContext.instances = [];
  vi.stubGlobal("AudioContext", FakeAudioContext);
  Object.defineProperty(window, "AudioContext", {
    value: FakeAudioContext,
    configurable: true,
    writable: true,
  });
  vi.stubGlobal(
    "Audio",
    class {
      loop = false;
      preload = "";
      crossOrigin = "";
      src = "";
      play() {
        return Promise.resolve();
      }
      pause() {}
    },
  );
};

const URL_A = "https://tracks.test/a.mp3";
const URL_B = "https://tracks.test/b.mp3";
const context = (): FakeAudioContext => FakeAudioContext.instances[0];
const masterGain = () => context().gains[0];
const incomingChannelGain = () => context().gains[2];

describe("ambient controller transitions", () => {
  let controller: AmbientSoundtrackController;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    installFakeAudio();
    controller = new AmbientSoundtrackController({ sfxFileLoader: async () => null });
    controller.init();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("still accepts a boolean third argument to force a transition", () => {
    expect(controller.transitionTo("mystery", URL_A)).toBe(true);

    expect(controller.transitionTo("tension", URL_B)).toBe(false);
    expect(controller.transitionTo("tension", URL_B, true)).toBe(true);
  });

  it("forces a transition through the options object, bypassing the cooldown", () => {
    controller.transitionTo("mystery", URL_A);

    expect(controller.transitionTo("tension", URL_B, { isForce: true })).toBe(true);
  });

  it("respects the cooldown when the options do not force", () => {
    controller.transitionTo("mystery", URL_A);

    expect(controller.transitionTo("tension", URL_B, { crossfadeSeconds: 1.5 })).toBe(false);
  });

  it("fades in over the requested crossfade and defaults to four seconds", () => {
    context().currentTime = 10;
    controller.transitionTo("mystery", URL_A, { isForce: true, crossfadeSeconds: 1.5 });
    const quick = incomingChannelGain().gain.calls.find((call) => call.kind === "exp");

    controller.transitionTo("tension", URL_B, true);
    const defaultFade = context().gains[1].gain.calls.filter((call) => call.kind === "exp");

    expect(quick).toEqual({ kind: "exp", value: 1, time: 11.5 });
    expect(defaultFade.at(-1)?.time).toBe(14);
  });
});

describe("ambient controller volume and mute", () => {
  let controller: AmbientSoundtrackController;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    installFakeAudio();
    controller = new AmbientSoundtrackController({ sfxFileLoader: async () => null });
    controller.init();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("muting during the resume ramp cancels the ramp and takes effect at once", () => {
    controller.hardMute();
    controller.resumeAmbient(1500);

    controller.toggleMute();

    const calls = masterGain().gain.calls;
    expect(calls.at(-2)?.kind).toBe("cancel");
    expect(calls.at(-1)).toMatchObject({ kind: "set", value: 0 });
  });

  it("changing the volume during the resume ramp lands at once", () => {
    controller.hardMute();
    controller.resumeAmbient(1500);

    controller.setVolume(0.25);

    expect(masterGain().gain.calls.at(-2)?.kind).toBe("cancel");
    expect(masterGain().gain.calls.at(-1)).toMatchObject({ kind: "set", value: 0.25 });
  });

  it("keeps the ambience cut while a volume change arrives in the dead air", () => {
    controller.hardMute();

    controller.setVolume(0.9);

    expect(masterGain().gain.calls.at(-1)).toMatchObject({ kind: "set", value: 0 });
  });

  it("brings the new volume back when the cut ends", () => {
    controller.hardMute();
    controller.setVolume(0.9);

    controller.resumeAmbient(1000);

    expect(masterGain().gain.calls.filter((c) => c.kind === "linear").at(-1)?.value).toBe(0.9);
  });

  it("follows a mute or volume change in the middle of a playing cue", async () => {
    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    const sfxGain = context().gains.at(-1);

    controller.setVolume(0.2);
    expect(sfxGain?.gain.value).toBeCloseTo(0.2);
    controller.toggleMute();
    expect(sfxGain?.gain.value).toBe(0);

    context().sources[0].finish();
    await playing;
  });

  it("stops following preference changes once the cue has ended", async () => {
    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    const sfxGain = context().gains.at(-1);
    context().sources[0].finish();
    await playing;
    const callsAtEnd = sfxGain?.gain.calls.length;

    controller.setVolume(0.1);

    expect(sfxGain?.gain.calls.length).toBe(callsAtEnd);
  });
});

describe("ambient controller phantom ambience", () => {
  let controller: AmbientSoundtrackController;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    installFakeAudio();
    controller = new AmbientSoundtrackController({ sfxFileLoader: async () => null });
    controller.init();
  });

  afterEach(() => {
    controller.stop();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("whispers within 20 to 60 seconds, quietly, through the master gain", () => {
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime(WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS);

    expect(context().sources.length).toBe(1);
    const whisperGain = context().gains.at(-1);
    expect(whisperGain?.gain.value).toBeLessThanOrEqual(PHANTOM_MAX_GAIN);
    expect(whisperGain?.connections).toContain(masterGain());
  });

  it("does nothing before the first interval", () => {
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime(WHISPER_MIN_DELAY_MS - 1);

    expect(context().sources).toHaveLength(0);
  });

  it("keeps whispering at intervals", () => {
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime((WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS) * 3);

    expect(context().sources.length).toBeGreaterThanOrEqual(3);
  });

  it("stops when switched off", () => {
    controller.setPhantomAmbience(1, "pt-1");
    controller.setPhantomAmbience(0);
    vi.advanceTimersByTime((WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS) * 3);

    expect(context().sources).toHaveLength(0);
  });

  it("stops with the soundtrack", () => {
    controller.setPhantomAmbience(1, "pt-1");
    controller.stop();
    vi.advanceTimersByTime((WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS) * 3);

    expect(context().sources).toHaveLength(0);
  });

  it("does not restart its schedule when asked again with the same seed", () => {
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime(WHISPER_MIN_DELAY_MS - 1000);
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime(WHISPER_DELAY_SPAN_MS + 1000);

    expect(context().sources.length).toBeGreaterThanOrEqual(1);
  });

  it("whispers on the same schedule for the same seed", () => {
    const firstRun = (): number => {
      installFakeAudio();
      const fresh = new AmbientSoundtrackController({ sfxFileLoader: async () => null });
      fresh.setPhantomAmbience(1, "pt-7");
      let elapsed = 0;
      while (FakeAudioContext.instances[0].sources.length === 0 && elapsed < 70000) {
        vi.advanceTimersByTime(100);
        elapsed += 100;
      }
      fresh.stop();
      return elapsed;
    };

    expect(firstRun()).toBe(firstRun());
  });

  it("drops a whisper the browser has not allowed yet", () => {
    context().state = "suspended";
    controller.setPhantomAmbience(1, "pt-1");
    vi.advanceTimersByTime(WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS);

    expect(context().sources).toHaveLength(0);
  });
});
