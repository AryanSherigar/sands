import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { TIER_CROSSFADE_SECONDS, useTierAudio } from "../useTierAudio";

const transitionTo = vi.fn();
vi.mock("@/shared/lib/audio/ambient-soundtrack", () => ({
  ambientSoundtrack: {
    transitionTo: (...args: unknown[]) => transitionTo(...args),
    onMoodChange: vi.fn(),
    getVolume: () => 0.6,
    getIsMuted: () => false,
  },
}));

let releaseCues: (() => void) | null = null;
let areCuesRunning = false;
vi.mock("../../lib/atmosphereSubscriber", () => ({
  handleSensoryCue: vi.fn(),
  handleRuleRevealed: vi.fn(),
  shouldIgnoreNarratorMood: () => false,
  whenCuesIdle: () =>
    areCuesRunning
      ? new Promise<void>((resolve) => {
          releaseCues = resolve;
        })
      : Promise.resolve(),
}));

const TRACKS = {
  mystery: "https://tracks.test/mystery.mp3",
  tension: "https://tracks.test/tension.mp3",
  combat: "https://tracks.test/combat.mp3",
};

const setPlaythrough = (
  tier: string,
  overrides: Partial<PlaythroughData> = {},
): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      music_tracks: TRACKS,
      hud_hints: {
        meters: [],
        tier: {
          path: "tension_tier",
          hint: {
            kind: "tier",
            label: "Tension",
            mood_map: { uneasy: "mystery", tense: "tension", breaking: "combat" },
          },
          options: ["uneasy", "tense", "breaking"],
        },
      },
      state: { tension_tier: tier },
      ...overrides,
    } as unknown as PlaythroughData,
  });
};

const flush = async (): Promise<void> => {
  await act(async () => {
    await Promise.resolve();
  });
};

describe("useTierAudio", () => {
  beforeEach(() => {
    transitionTo.mockClear();
    areCuesRunning = false;
    releaseCues = null;
  });

  it("applies the current tier's mood on mount through the fast forced path", async () => {
    setPlaythrough("tense");

    renderHook(() => useTierAudio());
    await flush();

    expect(transitionTo).toHaveBeenCalledWith("tension", TRACKS.tension, {
      isForce: true,
      crossfadeSeconds: TIER_CROSSFADE_SECONDS,
      fallbackUrl: TRACKS.tension,
    });
    expect(TIER_CROSSFADE_SECONDS).toBe(1.5);
  });

  it("plays the tier's own track and keeps the mood track as the fallback", async () => {
    setPlaythrough("tense", {
      tier_tracks: { tense: "https://tracks.test/tier-tense.mp3" },
    });

    renderHook(() => useTierAudio());
    await flush();

    expect(transitionTo).toHaveBeenCalledWith(
      "tension",
      "https://tracks.test/tier-tense.mp3",
      expect.objectContaining({ fallbackUrl: TRACKS.tension }),
    );
  });

  it("uses the mood track for a tier that has no track of its own", async () => {
    setPlaythrough("tense", {
      tier_tracks: { breaking: "https://tracks.test/tier-breaking.mp3" },
    });

    renderHook(() => useTierAudio());
    await flush();

    expect(transitionTo).toHaveBeenCalledWith("tension", TRACKS.tension, expect.anything());
  });

  it("changes track when the tier changes even if both tiers share a mood", async () => {
    const tierTracks = {
      tense: "https://tracks.test/tier-tense.mp3",
      dread: "https://tracks.test/tier-dread.mp3",
    };
    const sharedMoodMap = { tense: "tension", dread: "tension" };
    const withTiers = (tier: string): void =>
      setPlaythrough(tier, {
        tier_tracks: tierTracks,
        hud_hints: {
          meters: [],
          tier: {
            path: "tension_tier",
            hint: { kind: "tier", label: "Tension", mood_map: sharedMoodMap },
            options: ["tense", "dread"],
          },
        },
      } as Partial<PlaythroughData>);
    withTiers("tense");
    renderHook(() => useTierAudio());
    await flush();

    act(() => withTiers("dread"));
    await flush();

    expect(transitionTo).toHaveBeenLastCalledWith(
      "tension",
      tierTracks.dread,
      expect.anything(),
    );
  });

  it("moves to the new mood when the tier changes", async () => {
    setPlaythrough("uneasy");
    renderHook(() => useTierAudio());
    await flush();

    act(() => setPlaythrough("breaking"));
    await flush();

    expect(transitionTo).toHaveBeenLastCalledWith("combat", TRACKS.combat, expect.anything());
  });

  it("does not transition again when an unrelated state change leaves the tier alone", async () => {
    setPlaythrough("tense");
    renderHook(() => useTierAudio());
    await flush();
    transitionTo.mockClear();

    act(() => {
      usePlayStore.setState((current) => ({
        playthrough: {
          ...(current.playthrough as PlaythroughData),
          state: { tension_tier: "tense", sanity: 10 },
        },
      }));
    });
    await flush();

    expect(transitionTo).not.toHaveBeenCalled();
  });

  it("waits for a running cue sequence to finish before changing the mood", async () => {
    areCuesRunning = true;
    setPlaythrough("tense");

    renderHook(() => useTierAudio());
    await flush();
    expect(transitionTo).not.toHaveBeenCalled();

    releaseCues?.();
    await flush();

    expect(transitionTo).toHaveBeenCalledTimes(1);
  });

  it("drops a change that was superseded while it waited", async () => {
    areCuesRunning = true;
    setPlaythrough("tense");
    renderHook(() => useTierAudio());
    await flush();
    const releaseFirst = releaseCues;

    act(() => setPlaythrough("breaking"));
    await flush();
    releaseFirst?.();
    releaseCues?.();
    await flush();

    expect(transitionTo).toHaveBeenCalledTimes(1);
    expect(transitionTo).toHaveBeenCalledWith("combat", TRACKS.combat, expect.anything());
  });

  it.each([
    ["no mood_map", { hud_hints: { meters: [], tier: { path: "tension_tier", hint: { kind: "tier", label: "T" }, options: ["tense"] } } }],
    ["atmosphere off", { enabled_tools: ["status_hud"] }],
    ["status_hud off", { enabled_tools: ["atmosphere"] }],
  ])("does nothing with %s", async (_label, overrides) => {
    setPlaythrough("tense", overrides as Partial<PlaythroughData>);

    renderHook(() => useTierAudio());
    await flush();

    expect(transitionTo).not.toHaveBeenCalled();
  });

  it("ignores a mapped value that is not a known mood", async () => {
    setPlaythrough("tense", {
      hud_hints: {
        meters: [],
        tier: {
          path: "tension_tier",
          hint: { kind: "tier", label: "T", mood_map: { tense: "sparkly" } },
          options: ["tense"],
        },
      },
    });

    renderHook(() => useTierAudio());
    await flush();

    expect(transitionTo).not.toHaveBeenCalled();
  });
});
