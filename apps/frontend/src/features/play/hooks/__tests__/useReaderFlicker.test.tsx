import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useAtmosphereStore } from "../../stores/atmosphere.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { POWER_FLICKER_MS, useReaderFlicker } from "../useReaderFlicker";

const OPTIONS = ["uneasy", "tense", "dread", "breaking"];

const setTier = (tier: string): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: {
        meters: [],
        tier: {
          path: "tension_tier",
          hint: { kind: "tier", label: "Tension" },
          options: OPTIONS,
        },
      },
      state: { tension_tier: tier },
    } as unknown as PlaythroughData,
  });
};

describe("useReaderFlicker", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    useAtmosphereStore.setState({ flickerNonce: 0 });
    setTier("uneasy");
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not flicker on mount", () => {
    const { result } = renderHook(() => useReaderFlicker());

    expect(result.current).toBe(false);
  });

  it("flickers for 250 ms when a cue cuts the ambience", () => {
    const { result } = renderHook(() => useReaderFlicker());

    act(() => useAtmosphereStore.getState().triggerFlicker());
    expect(result.current).toBe(true);

    act(() => {
      vi.advanceTimersByTime(POWER_FLICKER_MS);
    });
    expect(result.current).toBe(false);
  });

  it("flickers when the tension tier rises but not when it falls", () => {
    const { result } = renderHook(() => useReaderFlicker());

    act(() => setTier("dread"));
    expect(result.current).toBe(true);
    act(() => {
      vi.advanceTimersByTime(POWER_FLICKER_MS);
    });

    act(() => setTier("tense"));
    expect(result.current).toBe(false);
  });

  it("never flickers under reduced sensory effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    const { result } = renderHook(() => useReaderFlicker());

    act(() => useAtmosphereStore.getState().triggerFlicker());
    act(() => setTier("breaking"));

    expect(result.current).toBe(false);
  });
});
