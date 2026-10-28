import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AmbientSoundtrackController } from "../ambient-soundtrack";
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

const masterGain = (context: FakeAudioContext) => context.gains[0];

describe("ambient controller cue support", () => {
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

  it("hardMute ramps the master gain to zero within 30 ms", () => {
    const context = FakeAudioContext.instances[0];
    context.currentTime = 10;

    controller.hardMute();

    const ramp = masterGain(context).gain.calls.find((c) => c.kind === "linear");
    expect(ramp).toEqual({ kind: "linear", value: 0, time: 10.03 });
  });

  it("hardMute cancels any earlier automation first", () => {
    const context = FakeAudioContext.instances[0];

    controller.hardMute();

    expect(masterGain(context).gain.calls[0].kind).toBe("cancel");
  });

  it("resumeAmbient ramps back to the user's volume", () => {
    const context = FakeAudioContext.instances[0];
    controller.setVolume(0.5);
    context.currentTime = 4;

    controller.resumeAmbient(1500);

    const ramp = masterGain(context).gain.calls.filter((c) => c.kind === "linear").at(-1);
    expect(ramp).toEqual({ kind: "linear", value: 0.5, time: 5.5 });
  });

  it("resumeAmbient never un-mutes a user who muted the game", () => {
    const context = FakeAudioContext.instances[0];
    controller.toggleMute();

    controller.hardMute();
    controller.resumeAmbient(1000);

    const ramp = masterGain(context).gain.calls.filter((c) => c.kind === "linear").at(-1);
    expect(ramp?.value).toBe(0);
  });

  it("playSfx waits the lead silence, then plays and resolves when the sound ends", async () => {
    const context = FakeAudioContext.instances[0];
    const done = vi.fn();

    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 800 });
    void playing.then(done);
    await vi.advanceTimersByTimeAsync(799);
    expect(context.sources).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(2);

    expect(context.sources).toHaveLength(1);
    expect(context.sources[0].hasStarted).toBe(true);
    expect(done).not.toHaveBeenCalled();
    context.sources[0].finish();
    await playing;
    expect(done).toHaveBeenCalled();
  });

  it("plays the sound outside the master gain so a hard cut cannot silence it", async () => {
    const context = FakeAudioContext.instances[0];

    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    const source = context.sources[0];

    expect(source.connections).not.toContain(masterGain(context));
    source.finish();
    await playing;
  });

  it("makes the sound follow the player's volume", async () => {
    const context = FakeAudioContext.instances[0];
    controller.setVolume(0.4);

    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    context.sources[0].finish();
    await playing;

    const sfxGain = context.gains.at(-1);
    expect(sfxGain?.gain.value).toBeCloseTo(0.4);
  });

  it("keeps the timing but makes no sound when the player muted", async () => {
    const context = FakeAudioContext.instances[0];
    controller.toggleMute();

    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    context.sources[0].finish();
    await playing;

    expect(context.gains.at(-1)?.gain.value).toBe(0);
  });

  it("drops the cue when the browser has not allowed audio yet", async () => {
    const context = FakeAudioContext.instances[0];
    context.state = "suspended";
    context.resume = () => Promise.resolve();

    const playing = controller.playSfx("phone_ring", { leadSilenceMs: 0 });
    await vi.advanceTimersByTimeAsync(1);
    await playing;

    expect(context.sources).toHaveLength(0);
  });
});
