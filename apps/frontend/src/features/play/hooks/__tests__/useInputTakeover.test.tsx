import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { ClientEffect } from "@/shared/lib/client-effects/clientEffects.types";
import { usePlayStore } from "../../stores/play.store";
import { useInputTakeover } from "../useInputTakeover";

const LINE = "Get me out of here, Orr";
const EFFECT: ClientEffect = {
  kind: "input_takeover",
  params: { text: LINE, lock_ms: 4500, type_ms_per_char: 50 },
};

describe("useInputTakeover", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    usePlayStore.setState({
      active_client_effect: null,
      queued_client_effects: [],
      is_action_drawer_open: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("is idle without a takeover", () => {
    const { result } = renderHook(() => useInputTakeover());
    expect(result.current).toEqual({ takeoverText: null, isLocked: false });
  });

  it("types the line, locks, then finishes", () => {
    usePlayStore.setState({ active_client_effect: EFFECT });
    const { result } = renderHook(() => useInputTakeover());
    expect(usePlayStore.getState().is_action_drawer_open).toBe(true);

    act(() => vi.advanceTimersByTime(50 * 3));
    expect(result.current.takeoverText).toBe("Get");
    expect(result.current.isLocked).toBe(true);

    act(() => vi.advanceTimersByTime(50 * LINE.length));
    expect(result.current.takeoverText).toBe(LINE);

    act(() => vi.advanceTimersByTime(4500));
    expect(result.current.takeoverText).toBeNull();
    expect(result.current.isLocked).toBe(false);
    expect(usePlayStore.getState().active_client_effect).toBeNull();
  });

  it("shows the whole line without a lock when effects are reduced", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    usePlayStore.setState({ active_client_effect: EFFECT });
    const { result } = renderHook(() => useInputTakeover());
    expect(result.current.takeoverText).toBe(LINE);
    expect(result.current.isLocked).toBe(false);

    act(() => vi.advanceTimersByTime(4500));
    expect(result.current.takeoverText).toBeNull();
    expect(usePlayStore.getState().active_client_effect).toBeNull();
  });

  it("ignores other effect kinds", () => {
    usePlayStore.setState({
      active_client_effect: { kind: "phone_echo", params: { record_ms: 6000, delay_ms: 2500 } },
    });
    const { result } = renderHook(() => useInputTakeover());
    expect(result.current.takeoverText).toBeNull();
    expect(usePlayStore.getState().is_action_drawer_open).toBe(false);
  });
});
