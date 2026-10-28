import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { useSanityBand } from "../useSanityBand";

const meter = {
  path: "sanity",
  hint: {
    kind: "meter" as const,
    label: "Sanity",
    clamp_min: 0,
    clamp_max: 100,
    effects: { moderate_below: 50, critical_below: 25 },
  },
};

const setPlaythrough = (overrides: Partial<PlaythroughData> = {}): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: { meters: [meter] },
      state: { sanity: 80 },
      ...overrides,
    } as PlaythroughData,
  });
};

describe("useSanityBand", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });

  it.each([
    [80, "none"],
    [40, "moderate"],
    [10, "critical"],
    [-8, "critical"],
  ])("reads %i as %s", (sanity, band) => {
    setPlaythrough({ state: { sanity } });

    const { result } = renderHook(() => useSanityBand());

    expect(result.current.band).toBe(band);
  });

  it("follows the state as it changes", () => {
    setPlaythrough();
    const { result } = renderHook(() => useSanityBand());

    act(() => setPlaythrough({ state: { sanity: 10 } }));

    expect(result.current.band).toBe("critical");
  });

  it("is none unless both atmosphere and status_hud are on", () => {
    setPlaythrough({ enabled_tools: ["atmosphere"], state: { sanity: 10 } });
    expect(renderHook(() => useSanityBand()).result.current.band).toBe("none");

    setPlaythrough({ enabled_tools: ["status_hud"], state: { sanity: 10 } });
    expect(renderHook(() => useSanityBand()).result.current.band).toBe("none");
  });

  it("is none when the meter defines no effects", () => {
    setPlaythrough({
      hud_hints: {
        meters: [{ ...meter, hint: { ...meter.hint, effects: undefined } }],
      },
      state: { sanity: 5 },
    });

    expect(renderHook(() => useSanityBand()).result.current.band).toBe("none");
  });

  it("is none when the reader reduces sensory effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    setPlaythrough({ state: { sanity: 5 } });

    expect(renderHook(() => useSanityBand()).result.current.band).toBe("none");
  });

  it("is none without a numeric value yet", () => {
    setPlaythrough({ state: {} });

    expect(renderHook(() => useSanityBand()).result.current.band).toBe("none");
  });
});
