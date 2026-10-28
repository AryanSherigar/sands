import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ActiveRuleCheck } from "@/shared/types/check.types";
import { useRuleCheckTimer } from "../useRuleCheckTimer";

const START = 1_000_000;

const activeCheck = (
  overrides: Partial<ActiveRuleCheck> = {},
): ActiveRuleCheck => ({
  check_id: "chk-1",
  kind: "timed_choice",
  prompt: "The phone rings.",
  options: [],
  window_ms: 12000,
  issued_at: 0,
  initial_remaining_ms: 12000,
  started_at_client_ms: START,
  ...overrides,
});

describe("useRuleCheckTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with the whole remaining window", () => {
    const { result } = renderHook(() =>
      useRuleCheckTimer(activeCheck(), vi.fn()),
    );

    expect(result.current).toBe(12000);
  });

  it("counts down as time passes", () => {
    const { result } = renderHook(() =>
      useRuleCheckTimer(activeCheck(), vi.fn()),
    );

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current).toBeLessThanOrEqual(7100);
    expect(result.current).toBeGreaterThanOrEqual(6900);
  });

  it("calls onExpire once when the time runs out", () => {
    const onExpire = vi.fn();
    renderHook(() => useRuleCheckTimer(activeCheck(), onExpire));

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("does not call onExpire before the time runs out", () => {
    const onExpire = vi.fn();
    renderHook(() => useRuleCheckTimer(activeCheck(), onExpire));

    act(() => {
      vi.advanceTimersByTime(11_000);
    });

    expect(onExpire).not.toHaveBeenCalled();
  });

  it("expires immediately when no time was left on arrival", () => {
    const onExpire = vi.fn();
    renderHook(() =>
      useRuleCheckTimer(activeCheck({ initial_remaining_ms: 0 }), onExpire),
    );

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("does nothing and reports zero when there is no prompt", () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() => useRuleCheckTimer(null, onExpire));

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(result.current).toBe(0);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("stops counting once the prompt goes away", () => {
    const onExpire = vi.fn();
    const { rerender } = renderHook(
      ({ check }) => useRuleCheckTimer(check, onExpire),
      { initialProps: { check: activeCheck() as ActiveRuleCheck | null } },
    );

    rerender({ check: null });
    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(onExpire).not.toHaveBeenCalled();
  });

  it("restarts for a different prompt", () => {
    const onExpire = vi.fn();
    const { rerender } = renderHook(
      ({ check }) => useRuleCheckTimer(check, onExpire),
      { initialProps: { check: activeCheck() } },
    );
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    rerender({
      check: activeCheck({
        check_id: "chk-2",
        started_at_client_ms: Date.now(),
      }),
    });
    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    expect(onExpire).not.toHaveBeenCalled();
  });
});
