import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { useEnabledTools } from "../useEnabledTools";

const playthroughWith = (
  enabledTools: string[] | undefined,
): PlaythroughData =>
  ({ playthrough_id: "pt-1", enabled_tools: enabledTools }) as PlaythroughData;

describe("useEnabledTools", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
  });

  it("returns an empty list when there is no playthrough", () => {
    const { result } = renderHook(() => useEnabledTools());

    expect(result.current).toEqual([]);
  });

  it("returns an empty list for an old playthrough without enabled_tools", () => {
    usePlayStore.setState({ playthrough: playthroughWith(undefined) });

    const { result } = renderHook(() => useEnabledTools());

    expect(result.current).toEqual([]);
  });

  it("returns the pinned tools", () => {
    usePlayStore.setState({ playthrough: playthroughWith(["atmosphere"]) });

    const { result } = renderHook(() => useEnabledTools());

    expect(result.current).toEqual(["atmosphere"]);
  });

  it("returns the same empty array reference across renders", () => {
    const { result, rerender } = renderHook(() => useEnabledTools());
    const first = result.current;

    rerender();

    expect(result.current).toBe(first);
  });
});
