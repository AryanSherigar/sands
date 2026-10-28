import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { INTRUSIVE_INTERVAL_MS, useIntrusivePlaceholder } from "../useIntrusivePlaceholder";

const STANDARD = "Action (Do): what do you do...";
const THOUGHTS = ["don't turn around", "it heard you breathe"];

const setPlaythrough = (sanity: number, thoughts: string[] = THOUGHTS): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: {
        meters: [
          {
            path: "sanity",
            hint: {
              kind: "meter",
              label: "Sanity",
              clamp_min: 0,
              clamp_max: 100,
              effects: { intrusive_below: 50, intrusive_thoughts: thoughts },
            },
          },
        ],
      },
      state: { sanity },
    } as unknown as PlaythroughData,
  });
};

const advance = (ms: number): void => {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
};

describe("useIntrusivePlaceholder", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts on the standard text and alternates every 7 seconds, in authored order", () => {
    setPlaythrough(30);
    const { result } = renderHook(() => useIntrusivePlaceholder(STANDARD, false, 0));
    expect(result.current).toEqual({ placeholder: STANDARD, isIntrusive: false });

    advance(INTRUSIVE_INTERVAL_MS);
    expect(result.current).toEqual({ placeholder: THOUGHTS[0], isIntrusive: true });

    advance(INTRUSIVE_INTERVAL_MS);
    expect(result.current.placeholder).toBe(STANDARD);

    advance(INTRUSIVE_INTERVAL_MS);
    expect(result.current.placeholder).toBe(THOUGHTS[1]);

    advance(INTRUSIVE_INTERVAL_MS * 2);
    expect(result.current.placeholder).toBe(THOUGHTS[0]);
  });

  it("is removed while the input has text", () => {
    setPlaythrough(30);
    const { result, rerender } = renderHook(
      ({ isSuppressed }) => useIntrusivePlaceholder(STANDARD, isSuppressed, 0),
      { initialProps: { isSuppressed: false } },
    );
    advance(INTRUSIVE_INTERVAL_MS);
    expect(result.current.isIntrusive).toBe(true);

    rerender({ isSuppressed: true });
    expect(result.current).toEqual({ placeholder: STANDARD, isIntrusive: false });

    advance(INTRUSIVE_INTERVAL_MS * 3);
    expect(result.current.isIntrusive).toBe(false);
  });

  it("goes back to the standard text and restarts when the input gains focus", () => {
    setPlaythrough(30);
    const { result, rerender } = renderHook(
      ({ restartToken }) => useIntrusivePlaceholder(STANDARD, false, restartToken),
      { initialProps: { restartToken: 0 } },
    );
    advance(INTRUSIVE_INTERVAL_MS);
    expect(result.current.isIntrusive).toBe(true);

    rerender({ restartToken: 1 });
    expect(result.current).toEqual({ placeholder: STANDARD, isIntrusive: false });

    advance(INTRUSIVE_INTERVAL_MS - 1);
    expect(result.current.isIntrusive).toBe(false);
    advance(1);
    expect(result.current.placeholder).toBe(THOUGHTS[0]);
  });

  it("never shows a phrase at or above the threshold", () => {
    setPlaythrough(50);
    const { result } = renderHook(() => useIntrusivePlaceholder(STANDARD, false, 0));

    advance(INTRUSIVE_INTERVAL_MS * 4);

    expect(result.current.isIntrusive).toBe(false);
  });

  it("stays standard when the creator authored no phrases", () => {
    setPlaythrough(10, []);
    const { result } = renderHook(() => useIntrusivePlaceholder(STANDARD, false, 0));

    advance(INTRUSIVE_INTERVAL_MS * 4);

    expect(result.current.placeholder).toBe(STANDARD);
  });

  it("stays standard under reduced sensory effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    setPlaythrough(10);
    const { result } = renderHook(() => useIntrusivePlaceholder(STANDARD, false, 0));

    advance(INTRUSIVE_INTERVAL_MS * 2);

    expect(result.current.isIntrusive).toBe(false);
  });
});
