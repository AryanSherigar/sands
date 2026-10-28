import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useViewport } from "./useViewport";

const SIZE = { width: 1000, height: 500 };

describe("useViewport", () => {
  it("starts showing the whole picture", () => {
    const { result } = renderHook(() => useViewport(SIZE));
    expect(result.current.viewBox).toBe("0 0 1000 500");
  });

  it("zooms in around a point and clamps to the picture", () => {
    const { result } = renderHook(() => useViewport(SIZE));
    act(() => result.current.zoomTo({ x: 100, y: 50 }, 4));
    expect(result.current.viewBox).toBe("0 0 250 125");
    act(() => result.current.zoomTo({ x: 900, y: 450 }, 4));
    expect(result.current.viewBox).toBe("750 375 250 125");
  });

  it("resets to the whole picture", () => {
    const { result } = renderHook(() => useViewport(SIZE));
    act(() => result.current.zoomTo({ x: 500, y: 250 }, 2));
    act(() => result.current.reset());
    expect(result.current.viewBox).toBe("0 0 1000 500");
  });

  it("pans by raster units without leaving the picture", () => {
    const { result } = renderHook(() => useViewport(SIZE));
    act(() => result.current.zoomTo({ x: 500, y: 250 }, 2));
    act(() => result.current.panBy(10000, 10000));
    expect(result.current.viewBox).toBe("500 250 500 250");
  });
});
