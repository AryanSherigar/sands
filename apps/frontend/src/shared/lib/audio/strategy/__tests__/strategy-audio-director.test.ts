import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  StrategyAudioDirector,
  FALLBACK_MOOD_MAP,
  resolveStrategyTrackUrl,
} from "../strategy-audio-director";
import type { StrategyAudioTarget } from "@/shared/types/strategy-audio.types";

interface AudioParamMock {
  value: number;
  setValueAtTime: ReturnType<typeof vi.fn>;
  exponentialRampToValueAtTime: ReturnType<typeof vi.fn>;
  linearRampToValueAtTime: ReturnType<typeof vi.fn>;
}

function createAudioParamMock(initialValue = 0): AudioParamMock {
  return {
    value: initialValue,
    setValueAtTime: vi.fn(function (this: AudioParamMock, val: number) {
      this.value = val;
    }),
    exponentialRampToValueAtTime: vi.fn(function (this: AudioParamMock, val: number) {
      this.value = val;
    }),
    linearRampToValueAtTime: vi.fn(function (this: AudioParamMock, val: number) {
      this.value = val;
    }),
  };
}

class MockGainNode {
  gain = createAudioParamMock(1);
  connections: unknown[] = [];
  connect = vi.fn((target: unknown) => {
    this.connections.push(target);
  });
  disconnect = vi.fn();
}

class MockBiquadFilterNode {
  type: BiquadFilterType = "lowpass";
  frequency = createAudioParamMock(350);
  connections: unknown[] = [];
  connect = vi.fn((target: unknown) => {
    this.connections.push(target);
  });
  disconnect = vi.fn();
}

class MockAudioContext {
  static instances: MockAudioContext[] = [];
  currentTime = 10;
  state: AudioContextState = "suspended";
  destination = { name: "destination" };
  gains: MockGainNode[] = [];
  filters: MockBiquadFilterNode[] = [];

  constructor() {
    MockAudioContext.instances.push(this);
  }

  createGain = vi.fn(() => {
    const gain = new MockGainNode();
    this.gains.push(gain);
    return gain;
  });

  createBiquadFilter = vi.fn(() => {
    const filter = new MockBiquadFilterNode();
    this.filters.push(filter);
    return filter;
  });

  resume = vi.fn(async () => {
    this.state = "running";
  });

  close = vi.fn(async () => {
    this.state = "closed";
  });
}

describe("StrategyAudioDirector", () => {
  let director: StrategyAudioDirector;

  beforeEach(() => {
    MockAudioContext.instances = [];
    vi.stubGlobal("AudioContext", MockAudioContext);
    vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(async () => {});
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("instantiation", () => {
    it("instantiates with default options (volume 0.7, unmuted)", () => {
      director = new StrategyAudioDirector();
      expect(director.getVolume()).toBe(0.7);
      expect(director.getIsMuted()).toBe(false);
    });

    it("instantiates with custom options", () => {
      director = new StrategyAudioDirector({ volume: 0.85, isMuted: true });
      expect(director.getVolume()).toBe(0.85);
      expect(director.getIsMuted()).toBe(true);
    });
  });

  describe("volume and mute controls", () => {
    it("updates volume within [0, 1] range and sets master gain when unmuted", () => {
      director = new StrategyAudioDirector({ volume: 0.7, isMuted: false });
      // Apply target to instantiate graph
      director.applyTarget({
        ambientTrack: "plains",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      const masterGain = ctx.gains[0];

      director.setVolume(0.4);
      expect(director.getVolume()).toBe(0.4);
      expect(masterGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.4, expect.any(Number));

      // Test clamping
      director.setVolume(1.5);
      expect(director.getVolume()).toBe(1.0);

      director.setVolume(-0.2);
      expect(director.getVolume()).toBe(0.0);
    });

    it("clamps zero volume to GAIN_EPSILON on audio ramp", () => {
      director = new StrategyAudioDirector({ volume: 0.5, isMuted: false });
      director.applyTarget({
        ambientTrack: "plains",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      const masterGain = ctx.gains[0];

      director.setVolume(0);
      expect(masterGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.0001, expect.any(Number));
    });

    it("updates mute state and mutes/unmutes master gain", () => {
      director = new StrategyAudioDirector({ volume: 0.8, isMuted: false });
      director.applyTarget({
        ambientTrack: "arid",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      const masterGain = ctx.gains[0];

      // Mute
      director.setIsMuted(true);
      expect(director.getIsMuted()).toBe(true);
      expect(masterGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.0001, expect.any(Number));

      // Unmute restores volume
      director.setIsMuted(false);
      expect(director.getIsMuted()).toBe(false);
      expect(masterGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.8, expect.any(Number));
    });

    it("does not restore audible master gain on volume change if muted", () => {
      director = new StrategyAudioDirector({ volume: 0.8, isMuted: true });
      director.applyTarget({
        ambientTrack: "arid",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      const masterGain = ctx.gains[0];
      masterGain.gain.exponentialRampToValueAtTime.mockClear();

      director.setVolume(0.9);
      expect(director.getVolume()).toBe(0.9);
      expect(masterGain.gain.exponentialRampToValueAtTime).not.toHaveBeenCalled();
    });
  });

  describe("4-layer audio graph topology and target updates", () => {
    it("wires the 4-layer node graph correctly", () => {
      director = new StrategyAudioDirector();
      director.applyTarget({
        ambientTrack: "arid",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      expect(ctx.gains.length).toBe(5); // master, ambient, mood, context, stinger
      expect(ctx.filters.length).toBe(1); // winter lowpass

      const [masterGain, ambientGain, moodGain, contextGain, stingerGain] = ctx.gains;
      const winterFilter = ctx.filters[0];

      // Ambient -> winterFilter -> masterGain
      expect(ambientGain.connections).toContain(winterFilter);
      expect(winterFilter.connections).toContain(masterGain);

      // Mood, Context, Stinger -> masterGain
      expect(moodGain.connections).toContain(masterGain);
      expect(contextGain.connections).toContain(masterGain);
      expect(stingerGain.connections).toContain(masterGain);

      // Master -> destination
      expect(masterGain.connections).toContain(ctx.destination);
    });

    it("smoothly ramps ambient, mood, and context gains with floor 0.0001", () => {
      director = new StrategyAudioDirector();
      const target: StrategyAudioTarget = {
        ambientTrack: "coast",
        ambientGain: 0.25,
        isWinterMuffled: false,
        strategicMood: "war",
        moodGain: 0.7,
        contextTrack: "court",
        contextGain: 0.4,
        pendingStinger: null,
      };

      director.applyTarget(target);

      const ctx = MockAudioContext.instances[0];
      const [, ambientGain, moodGain, contextGain] = ctx.gains;

      expect(ambientGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.25, 10 + 3.0);
      expect(moodGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.7, 10 + 3.0);
      expect(contextGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.4, 10 + 1.0);
    });

    it("floors zero gains to 0.0001 to prevent zero-crossing exceptions", () => {
      director = new StrategyAudioDirector();
      const target: StrategyAudioTarget = {
        ambientTrack: "mountains",
        ambientGain: 0,
        isWinterMuffled: false,
        strategicMood: "desolation",
        moodGain: 0,
        contextTrack: "none",
        contextGain: 0,
        pendingStinger: null,
      };

      director.applyTarget(target);

      const ctx = MockAudioContext.instances[0];
      const [, ambientGain, moodGain, contextGain] = ctx.gains;

      expect(ambientGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.0001, 10 + 3.0);
      expect(moodGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.0001, 10 + 3.0);
      expect(contextGain.gain.exponentialRampToValueAtTime).toHaveBeenCalledWith(0.0001, 10 + 1.0);
    });

    it("adjusts winter lowpass filter cutoff according to isWinterMuffled", () => {
      director = new StrategyAudioDirector();
      const winterTarget: StrategyAudioTarget = {
        ambientTrack: "mountains",
        ambientGain: 0.2,
        isWinterMuffled: true,
        strategicMood: "vigilance",
        moodGain: 0.5,
        contextTrack: "none",
        contextGain: 0,
        pendingStinger: null,
      };

      director.applyTarget(winterTarget);

      const ctx = MockAudioContext.instances[0];
      const winterFilter = ctx.filters[0];
      expect(winterFilter.type).toBe("lowpass");
      expect(winterFilter.frequency.exponentialRampToValueAtTime).toHaveBeenCalledWith(400, 10 + 3.0);

      const summerTarget: StrategyAudioTarget = {
        ...winterTarget,
        isWinterMuffled: false,
      };
      director.applyTarget(summerTarget);
      expect(winterFilter.frequency.exponentialRampToValueAtTime).toHaveBeenCalledWith(20000, 10 + 3.0);
    });

    it("triggers playStinger when pendingStinger is set", () => {
      director = new StrategyAudioDirector();
      const playStingerSpy = vi.spyOn(director, "playStinger");

      const targetWithStinger: StrategyAudioTarget = {
        ambientTrack: "plains",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "war",
        moodGain: 0.7,
        contextTrack: "tactical",
        contextGain: 0.5,
        pendingStinger: "war_declared",
      };

      director.applyTarget(targetWithStinger);
      expect(playStingerSpy).toHaveBeenCalledWith("war_declared");
    });
  });

  describe("unlock", () => {
    it("resumes audio context if suspended", async () => {
      director = new StrategyAudioDirector();
      director.applyTarget({
        ambientTrack: "plains",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      expect(ctx.state).toBe("suspended");

      director.unlock();
      expect(ctx.resume).toHaveBeenCalled();
    });

    it("handles unlock safely if audio context is not yet created", () => {
      director = new StrategyAudioDirector();
      expect(() => director.unlock()).not.toThrow();
    });
  });

  describe("cleanup and destroy", () => {
    it("closes audio context and tears down node graph on destroy", () => {
      director = new StrategyAudioDirector();
      director.applyTarget({
        ambientTrack: "plains",
        ambientGain: 0.2,
        isWinterMuffled: false,
        strategicMood: "pax",
        moodGain: 0.6,
        contextTrack: "none",
        contextGain: 0.0,
        pendingStinger: null,
      });

      const ctx = MockAudioContext.instances[0];
      director.destroy();

      expect(ctx.close).toHaveBeenCalled();
    });

    it("handles multiple calls to destroy safely", () => {
      director = new StrategyAudioDirector();
      expect(() => {
        director.destroy();
        director.destroy();
      }).not.toThrow();
    });
  });

  describe("fallback mapping", () => {
    it("defines fallback paths for all mood, stem, and terrain keys", () => {
      expect(FALLBACK_MOOD_MAP.pax).toBe("/audio/moods/peaceful.wav");
      expect(FALLBACK_MOOD_MAP.war).toBe("/audio/moods/combat.wav");
      expect(FALLBACK_MOOD_MAP.vigilance).toBe("/audio/moods/tension.wav");
      expect(FALLBACK_MOOD_MAP.desolation).toBe("/audio/moods/melancholy.wav");
      expect(FALLBACK_MOOD_MAP.court).toBe("/audio/moods/mystery.wav");
      expect(FALLBACK_MOOD_MAP.study).toBe("/audio/moods/peaceful.wav");
      expect(FALLBACK_MOOD_MAP.tactical).toBe("/audio/moods/tension.wav");
      expect(FALLBACK_MOOD_MAP.arid).toBe("/audio/moods/mystery.wav");
      expect(FALLBACK_MOOD_MAP.plains).toBe("/audio/moods/peaceful.wav");
      expect(FALLBACK_MOOD_MAP.coast).toBe("/audio/moods/peaceful.wav");
      expect(FALLBACK_MOOD_MAP.mountains).toBe("/audio/moods/mystery.wav");
    });
  });

  describe("track resolution", () => {
    it("only maps stems that exist and routes everything else through the mood files", () => {
      expect(resolveStrategyTrackUrl("pax")).toBe("/audio/strategy/stems/pax.mp3");
      expect(resolveStrategyTrackUrl("vigilance")).toBe("/audio/strategy/stems/vigilance.mp3");
      expect(resolveStrategyTrackUrl("war")).toBe("/audio/strategy/stems/war.mp3");
      expect(resolveStrategyTrackUrl("desolation")).toBe("/audio/strategy/stems/desolation.mp3");
      expect(resolveStrategyTrackUrl("unknown-key")).toBe("/audio/moods/peaceful.wav");
    });
  });
});
