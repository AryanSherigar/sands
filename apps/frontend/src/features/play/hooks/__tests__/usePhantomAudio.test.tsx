import { renderHook } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { usePhantomAudio } from "../usePhantomAudio";

const setPhantomAmbience = vi.fn();
vi.mock("@/shared/lib/audio/ambient-soundtrack", () => ({
  ambientSoundtrack: {
    setPhantomAmbience: (...args: unknown[]) => setPhantomAmbience(...args),
    onMoodChange: vi.fn(),
    getVolume: () => 0.6,
    getIsMuted: () => false,
  },
}));

const setSanity = (sanity: number, tools = ["status_hud", "atmosphere"]): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-9",
      enabled_tools: tools,
      hud_hints: {
        meters: [
          {
            path: "sanity",
            hint: {
              kind: "meter",
              label: "Sanity",
              clamp_min: 0,
              clamp_max: 100,
              effects: { moderate_below: 50, critical_below: 25 },
            },
          },
        ],
      },
      state: { sanity },
    } as unknown as PlaythroughData,
  });
};

describe("usePhantomAudio", () => {
  beforeEach(() => {
    setPhantomAmbience.mockClear();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });

  it("starts the whispers, seeded by the playthrough, once sanity drops below the threshold", () => {
    setSanity(80);
    renderHook(() => usePhantomAudio());
    expect(setPhantomAmbience).not.toHaveBeenCalled();

    act(() => setSanity(40));

    expect(setPhantomAmbience).toHaveBeenCalledWith(1, "pt-9");
  });

  it("stops them when sanity recovers", () => {
    setSanity(30);
    renderHook(() => usePhantomAudio());

    act(() => setSanity(90));

    expect(setPhantomAmbience).toHaveBeenLastCalledWith(0);
  });

  it("stops them on unmount", () => {
    setSanity(10);
    const { unmount } = renderHook(() => usePhantomAudio());

    unmount();

    expect(setPhantomAmbience).toHaveBeenLastCalledWith(0);
  });

  it("stays off under reduced sensory effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    setSanity(10);

    renderHook(() => usePhantomAudio());

    expect(setPhantomAmbience).not.toHaveBeenCalledWith(1, expect.anything());
  });

  it("stays off without both tools", () => {
    setSanity(10, ["atmosphere"]);

    renderHook(() => usePhantomAudio());

    expect(setPhantomAmbience).not.toHaveBeenCalledWith(1, expect.anything());
  });
});
