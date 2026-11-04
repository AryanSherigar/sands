import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeAudioContext } from "@/shared/lib/audio/__tests__/fakeAudioContext";
import { usePlayStore } from "../../stores/play.store";
import { useCrowdAudio } from "../useCrowdAudio";

const CHEER = { mood: "cheer", intensity: 2 } as const;

describe("useCrowdAudio", () => {
  beforeEach(() => {
    FakeAudioContext.instances = [];
    vi.stubGlobal("AudioContext", FakeAudioContext);
    usePlayStore.setState({ is_audio_muted: false, audio_volume: 0.6 });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("creates no audio context until a reaction is played", () => {
    renderHook(() => useCrowdAudio());
    expect(FakeAudioContext.instances).toHaveLength(0);
  });

  it("plays a reaction at the player's current volume", () => {
    const { result } = renderHook(() => useCrowdAudio());
    result.current.playReaction(CHEER);
    const context = FakeAudioContext.instances[0];
    expect(context?.sources.filter((source) => source.hasStarted)).toHaveLength(1);
    expect(context?.gains[0]?.gain.value).toBe(0.6);
  });

  it("reuses one context across reactions", () => {
    const { result } = renderHook(() => useCrowdAudio());
    result.current.playReaction(CHEER);
    result.current.playReaction({ mood: "murmur", intensity: 1 });
    expect(FakeAudioContext.instances).toHaveLength(1);
  });

  it("stays silent when the player has muted audio", () => {
    usePlayStore.setState({ is_audio_muted: true });
    const { result } = renderHook(() => useCrowdAudio());
    result.current.playReaction(CHEER);
    const started = FakeAudioContext.instances[0]?.sources.filter((source) => source.hasStarted) ?? [];
    expect(started).toHaveLength(0);
  });
});
