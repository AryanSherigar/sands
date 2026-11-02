import { act, renderHook } from "@testing-library/react";
import { beforeEach, afterEach, describe, it, expect, vi } from "vitest";
import { usePlayStore } from "../../stores/play.store";
import type { StrategyWorldSnapshot } from "../../types/strategyPlay.types";
import type { StrategyUIContext } from "@/shared/types/strategy-audio.types";
import { StrategyAudioDirector } from "@/shared/lib/audio/strategy/strategy-audio-director";
import { useStrategyAudio } from "../useStrategyAudio";

const mockBaseWorld: StrategyWorldSnapshot = {
  playthrough_id: "test-playthrough",
  turn: 1,
  season: "spring",
  year: 1042,
  status: "active",
  orders_remaining: 3,
  my_faction: {
    id: "f_crown",
    name: "Crown of High Cairn",
    treasury: 120,
    ruler: { name: "King Lucan", health_band: "robust" },
    capital_region_id: "reg_cairn",
    stats: { military: 50, economy: 60, diplomacy: 50 },
  },
  regions: [
    {
      id: "reg_cairn",
      name: "High Cairn",
      owner_faction_id: "f_crown",
      terrain: "mountains",
      unrest: 10,
      manpower: 500,
      is_under_siege: false,
    },
  ],
  armies: [],
  wars: [],
  rivals: [],
  event_log: [],
  queued_orders: [],
} as unknown as StrategyWorldSnapshot;

describe("useStrategyAudio", () => {
  let destroySpy: ReturnType<typeof vi.spyOn>;
  let applyTargetSpy: ReturnType<typeof vi.spyOn>;
  let unlockSpy: ReturnType<typeof vi.spyOn>;
  let setIsMutedSpy: ReturnType<typeof vi.spyOn>;
  let setVolumeSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    usePlayStore.setState({
      is_audio_muted: false,
      audio_volume: 0.75,
    });

    destroySpy = vi.spyOn(StrategyAudioDirector.prototype, "destroy");
    applyTargetSpy = vi.spyOn(StrategyAudioDirector.prototype, "applyTarget");
    unlockSpy = vi.spyOn(StrategyAudioDirector.prototype, "unlock");
    setIsMutedSpy = vi.spyOn(StrategyAudioDirector.prototype, "setIsMuted");
    setVolumeSpy = vi.spyOn(StrategyAudioDirector.prototype, "setVolume");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial render and unmount cleanup", () => {
    it("instantiates director, applies initial target, and destroys on unmount", () => {
      const { unmount } = renderHook(() =>
        useStrategyAudio({
          worldState: mockBaseWorld,
          uiContext: "map",
          seed: "test-seed",
        }),
      );

      expect(applyTargetSpy).toHaveBeenCalledTimes(1);
      const firstTarget = applyTargetSpy.mock.calls[0][0];
      expect(firstTarget.strategicMood).toBe("pax");
      expect(firstTarget.contextTrack).toBe("none");

      expect(destroySpy).not.toHaveBeenCalled();
      unmount();
      expect(destroySpy).toHaveBeenCalledTimes(1);
    });

    it("handles null or undefined worldState gracefully without throwing", () => {
      const { rerender, unmount } = renderHook(
        ({ world }: { world: StrategyWorldSnapshot | null }) =>
          useStrategyAudio({
            worldState: world,
            uiContext: "map",
          }),
        { initialProps: { world: null as StrategyWorldSnapshot | null } },
      );

      expect(applyTargetSpy).not.toHaveBeenCalled();

      rerender({ world: mockBaseWorld });
      expect(applyTargetSpy).toHaveBeenCalledTimes(1);

      unmount();
      expect(destroySpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("browser autoplay unlock event listeners", () => {
    it("registers pointerdown and keydown listeners and calls unlock on pointerdown", () => {
      const addEventListenerSpy = vi.spyOn(window, "addEventListener");
      const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

      const { unmount } = renderHook(() =>
        useStrategyAudio({
          worldState: mockBaseWorld,
          uiContext: "map",
        }),
      );

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "pointerdown",
        expect.any(Function),
        { once: true },
      );
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
        { once: true },
      );

      act(() => {
        window.dispatchEvent(new Event("pointerdown"));
      });

      expect(unlockSpy).toHaveBeenCalledTimes(1);

      unmount();
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "pointerdown",
        expect.any(Function),
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function),
      );
    });

    it("calls unlock on keydown event", () => {
      renderHook(() =>
        useStrategyAudio({
          worldState: mockBaseWorld,
          uiContext: "map",
        }),
      );

      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      expect(unlockSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("adapting to context changes", () => {
    it("adapts through map -> negotiation -> letter and updates audio target", () => {
      const { rerender } = renderHook(
        ({ context }: { context: StrategyUIContext }) =>
          useStrategyAudio({
            worldState: mockBaseWorld,
            uiContext: context,
            seed: "test-seed",
          }),
        { initialProps: { context: "map" as StrategyUIContext } },
      );

      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          contextTrack: "none",
          contextGain: 0.0,
        }),
      );

      rerender({ context: "negotiation" });
      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          contextTrack: "court",
          contextGain: 0.4,
        }),
      );

      rerender({ context: "letter" });
      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          contextTrack: "study",
          contextGain: 0.45,
        }),
      );
    });
  });

  describe("subscribing to audio preferences from usePlayStore", () => {
    it("updates director when is_audio_muted changes", () => {
      renderHook(() =>
        useStrategyAudio({
          worldState: mockBaseWorld,
          uiContext: "map",
        }),
      );

      act(() => {
        usePlayStore.setState({ is_audio_muted: true });
      });

      expect(setIsMutedSpy).toHaveBeenCalledWith(true);

      act(() => {
        usePlayStore.setState({ is_audio_muted: false });
      });

      expect(setIsMutedSpy).toHaveBeenCalledWith(false);
    });

    it("updates director when audio_volume changes", () => {
      renderHook(() =>
        useStrategyAudio({
          worldState: mockBaseWorld,
          uiContext: "map",
        }),
      );

      act(() => {
        usePlayStore.setState({ audio_volume: 0.25 });
      });

      expect(setVolumeSpy).toHaveBeenCalledWith(0.25);
    });
  });

  describe("replay scrubbing and state progression", () => {
    it("updates audio target when scrubbing to historical snapshot or advancing turn", () => {
      const { rerender } = renderHook(
        ({ world }: { world: StrategyWorldSnapshot }) =>
          useStrategyAudio({
            worldState: world,
            uiContext: "map",
            seed: "test-seed",
          }),
        { initialProps: { world: mockBaseWorld } },
      );

      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          strategicMood: "pax",
        }),
      );

      // Scrub or advance to turn with active war
      const warWorld: StrategyWorldSnapshot = {
        ...mockBaseWorld,
        turn: 4,
        wars: [
          {
            war_id: "war-iron",
            attacker_faction_id: "f_iron",
            defender_faction_id: "f_crown",
            war_score: -10,
          },
        ],
      };

      rerender({ world: warWorld });
      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          strategicMood: "war",
        }),
      );

      // Scrub back to initial turn 1 peaceful snapshot
      rerender({ world: mockBaseWorld });
      expect(applyTargetSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          strategicMood: "pax",
        }),
      );
    });
  });
});
