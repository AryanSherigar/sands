import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useWindowScroll } from "../useWindowScroll";

const scrollTo = (top: number): void => {
  Object.defineProperty(window, "scrollY", { value: top, configurable: true });
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
};

describe("useWindowScroll", () => {
  it("starts unscrolled", () => {
    scrollTo(0);
    const { result } = renderHook(() => useWindowScroll());
    expect(result.current).toEqual({ isScrolled: false, isPastHero: false });
  });

  it("marks scrolled past 24px but not past the hero", () => {
    const { result } = renderHook(() => useWindowScroll());
    scrollTo(40);
    expect(result.current).toEqual({ isScrolled: true, isPastHero: false });
  });

  it("marks past hero when scrolled far", () => {
    const { result } = renderHook(() => useWindowScroll());
    scrollTo(900);
    expect(result.current.isPastHero).toBe(true);
  });
});
