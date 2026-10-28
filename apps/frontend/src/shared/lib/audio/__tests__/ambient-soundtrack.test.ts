import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
  type MockInstance,
} from "vitest";
import { AmbientSoundtrackController } from "../ambient-soundtrack";

describe("AmbientSoundtrackController", () => {
  let controller: AmbientSoundtrackController;

  beforeEach(() => {
    localStorage.clear();
    controller = new AmbientSoundtrackController();
  });

  it("initializes with default volume and unmuted state", () => {
    expect(controller.getVolume()).toBe(0.6);
    expect(controller.getIsMuted()).toBe(false);
    expect(controller.getMood()).toBeNull();
  });

  it("clamps volume values within [0.0, 1.0]", () => {
    controller.setVolume(1.5);
    expect(controller.getVolume()).toBe(1.0);

    controller.setVolume(-0.5);
    expect(controller.getVolume()).toBe(0.0);

    controller.setVolume(0.75);
    expect(controller.getVolume()).toBe(0.75);
  });

  it("toggles mute state", () => {
    expect(controller.getIsMuted()).toBe(false);
    const muted = controller.toggleMute();
    expect(muted).toBe(true);
    expect(controller.getIsMuted()).toBe(true);

    const unmuted = controller.toggleMute();
    expect(unmuted).toBe(false);
    expect(controller.getIsMuted()).toBe(false);
  });

  it("notifies isolated audio consumers when global preferences change", () => {
    const listener = vi.fn();
    const unsubscribe = controller.onAudioPreferenceChange(listener);

    controller.setVolume(0.4);
    controller.toggleMute();
    unsubscribe();
    controller.setVolume(0.8);

    expect(listener).toHaveBeenCalledTimes(2);
    expect(listener).toHaveBeenNthCalledWith(1, {
      volume: 0.4,
      isMuted: false,
    });
    expect(listener).toHaveBeenNthCalledWith(2, { volume: 0.4, isMuted: true });
  });

  it("transitions to new mood and ignores duplicate transitions", () => {
    const firstTransition = controller.transitionTo(
      "peaceful",
      "https://example.com/peaceful.wav",
      true,
    );
    expect(firstTransition).toBe(true);
    expect(controller.getMood()).toBe("peaceful");

    const duplicateTransition = controller.transitionTo(
      "peaceful",
      "https://example.com/peaceful.wav",
    );
    expect(duplicateTransition).toBe(false);
  });

  it("enforces cooldown for non-combat transitions but allows combat escalation", () => {
    controller.transitionTo(
      "peaceful",
      "https://example.com/peaceful.wav",
      true,
    );

    // Non-combat transition immediately after should be throttled by cooldown
    const nonCombatAttempt = controller.transitionTo(
      "mystery",
      "https://example.com/mystery.wav",
    );
    expect(nonCombatAttempt).toBe(false);
    expect(controller.getMood()).toBe("peaceful");

    // Combat transition bypasses cooldown
    const combatAttempt = controller.transitionTo(
      "combat",
      "https://example.com/combat.wav",
    );
    expect(combatAttempt).toBe(true);
    expect(controller.getMood()).toBe("combat");
  });

  it("uses a custom track URL when one is provided", () => {
    controller.transitionTo("peaceful", "https://example.com/custom.wav", true);
    expect(controller.getCurrentTrackUrl()).toBe(
      "https://example.com/custom.wav",
    );
  });

  it("is a no-op when no track URL is resolvable", () => {
    const result = controller.transitionTo("peaceful", undefined, true);
    expect(result).toBe(false);
    expect(controller.getMood()).toBeNull();
  });

  it("persists settings in localStorage", () => {
    controller.setVolume(0.85);
    controller.toggleMute();

    expect(localStorage.getItem("sands_audio_volume")).toBe("0.85");
    expect(localStorage.getItem("sands_audio_muted")).toBe("true");

    const freshController = new AmbientSoundtrackController();
    expect(freshController.getVolume()).toBe(0.85);
    expect(freshController.getIsMuted()).toBe(true);
  });

  describe("autoplay unlock", () => {
    let playSpy: MockInstance<() => Promise<void>>;
    let originalAudioContext: typeof window.AudioContext;

    class StubAudioContext {
      state = "running";
      destination = {};
      createGain() {
        return {
          gain: {
            value: 0,
            setValueAtTime() {},
            exponentialRampToValueAtTime() {},
            cancelScheduledValues() {},
          },
          connect() {},
        };
      }
      createMediaElementSource() {
        return { connect() {} };
      }
      resume() {
        return Promise.resolve();
      }
    }

    beforeEach(() => {
      originalAudioContext = window.AudioContext;
      // @ts-expect-error test stub does not implement the full AudioContext surface
      window.AudioContext = StubAudioContext;
      playSpy = vi
        .spyOn(HTMLMediaElement.prototype, "play")
        .mockReturnValue(Promise.reject(new Error("autoplay blocked")));
    });

    afterEach(() => {
      window.AudioContext = originalAudioContext;
      playSpy.mockRestore();
    });

    it("retries the blocked channel's play() on the next user gesture", async () => {
      controller.transitionTo("peaceful", "https://example.com/peaceful.wav");

      // Let the rejected play() promise's .catch() actually run before the
      // unlock gesture fires.
      await new Promise((resolve) => setTimeout(resolve, 0));

      playSpy.mockReturnValue(Promise.resolve());
      window.dispatchEvent(new Event("pointerdown"));

      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(playSpy).toHaveBeenCalledTimes(2);
    });
  });

  describe("back-to-back crossfades", () => {
    let originalAudioContext: typeof window.AudioContext;
    let playSpy: MockInstance<() => Promise<void>>;
    const gains: FakeGainParam[] = [];

    interface GainEvent {
      time: number;
      value: number;
    }

    class FakeGainParam {
      value = 0;
      events: GainEvent[] = [];
      setValueAtTime(value: number, time: number) {
        this.events.push({ time, value });
      }
      exponentialRampToValueAtTime(value: number, time: number) {
        this.events.push({ time, value });
      }
      cancelScheduledValues(time: number) {
        this.events = this.events.filter((event) => event.time < time);
      }
      get finalValue() {
        const last = [...this.events].sort((a, b) => a.time - b.time).at(-1);
        return last?.value ?? this.value;
      }
    }

    class RecordingAudioContext {
      state = "running";
      currentTime = 0;
      destination = {};
      createGain() {
        const gain = new FakeGainParam();
        gains.push(gain);
        return { gain, connect() {} };
      }
      createMediaElementSource() {
        return { connect() {} };
      }
      resume() {
        return Promise.resolve();
      }
    }

    beforeEach(() => {
      gains.length = 0;
      originalAudioContext = window.AudioContext;
      // @ts-expect-error test stub does not implement the full AudioContext surface
      window.AudioContext = RecordingAudioContext;
      playSpy = vi
        .spyOn(HTMLMediaElement.prototype, "play")
        .mockReturnValue(Promise.resolve());
    });

    afterEach(() => {
      window.AudioContext = originalAudioContext;
      playSpy.mockRestore();
    });

    it("leaves the newest track audible when a second fade starts mid-fade", () => {
      controller.transitionTo("peaceful", "https://example.com/a.wav", true);
      controller.transitionTo("mystery", "https://example.com/b.wav", {
        isForce: true,
        crossfadeSeconds: 1.5,
      });

      // gains: [master, channelA, channelB]; B fades in first, then A.
      const [, channelAGain, channelBGain] = gains;
      expect(channelAGain.finalValue).toBe(1);
      expect(channelBGain.finalValue).toBeLessThan(0.001);
    });
  });
});
