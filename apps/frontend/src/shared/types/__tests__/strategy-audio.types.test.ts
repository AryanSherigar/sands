import { describe, it, expect } from "vitest";
import "../strategy-audio.types";
import type {
  StrategyUIContext,
  StrategicMood,
  AmbientTerrain,
  StrategyStingerEvent,
  StrategyContextTrack,
  StrategyAudioTarget,
  StrategyAudioEvaluatorOptions,
  StrategyAudioDirectorOptions,
} from "../strategy-audio.types";

describe("strategy-audio.types contract", () => {
  it("enforces valid audio target shapes", () => {
    const target: StrategyAudioTarget = {
      ambientTrack: "arid",
      ambientGain: 0.2,
      isWinterMuffled: false,
      strategicMood: "pax",
      moodGain: 0.6,
      contextTrack: "none",
      contextGain: 0.0,
      pendingStinger: null,
    };
    expect(target.ambientTrack).toBe("arid");
    expect(target.strategicMood).toBe("pax");
  });

  it("supports UI contexts and stinger events", () => {
    const uiContext: StrategyUIContext = "war_council";
    const stinger: StrategyStingerEvent = "war_declared";
    const terrain: AmbientTerrain = "mountains";
    const mood: StrategicMood = "war";
    const contextTrack: StrategyContextTrack = "tactical";

    const target: StrategyAudioTarget = {
      ambientTrack: terrain,
      ambientGain: 0.5,
      isWinterMuffled: true,
      strategicMood: mood,
      moodGain: 0.8,
      contextTrack,
      contextGain: 0.3,
      pendingStinger: stinger,
    };

    expect(uiContext).toBe("war_council");
    expect(target.pendingStinger).toBe("war_declared");
    expect(target.isWinterMuffled).toBe(true);
  });

  it("supports evaluator options", () => {
    const options: StrategyAudioEvaluatorOptions = {
      minHoldDurationMs: 5000,
    };
    expect(options.minHoldDurationMs).toBe(5000);
  });

  it("supports director options", () => {
    const options: StrategyAudioDirectorOptions = {
      volume: 0.8,
      isMuted: false,
    };
    expect(options.volume).toBe(0.8);
    expect(options.isMuted).toBe(false);
  });
});
