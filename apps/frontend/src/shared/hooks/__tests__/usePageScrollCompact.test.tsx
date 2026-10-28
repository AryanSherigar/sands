import { act, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { usePageScrollCompact } from "../usePageScrollCompact";
import { PAGE_SCROLL_ATTRIBUTE } from "@/shared/constants/scroll";

// requestAnimationFrame must not invoke its callback synchronously (real
// browsers never do): the hook assigns the returned handle to a ref *after*
// scheduling, so an inline callback resets that ref to null before the
// assignment overwrites it back to a non-null handle, silently disabling
// every frame after the first. Deferring via a queue avoids that reentrancy.
let pendingFrame: FrameRequestCallback | null = null;

const dispatchScroll = (scrollTop: number, hasAttribute: boolean): void => {
  const scroller = document.createElement("div");
  if (hasAttribute) scroller.setAttribute(PAGE_SCROLL_ATTRIBUTE, "");
  document.body.appendChild(scroller);
  Object.defineProperty(scroller, "scrollTop", { value: scrollTop });
  act(() => {
    scroller.dispatchEvent(new Event("scroll"));
  });
  document.body.removeChild(scroller);
  const frame = pendingFrame;
  pendingFrame = null;
  if (frame) act(() => frame(0));
};

describe("usePageScrollCompact", () => {
  const renderAt = (path: string) =>
    renderHook(() => usePageScrollCompact(), {
      wrapper: ({ children }) => (
        <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
      ),
    });

  beforeEach(() => {
    pendingFrame = null;
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      pendingFrame = cb;
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", () => {
      pendingFrame = null;
    });
  });

  it("starts expanded", () => {
    const { result } = renderAt("/discover");
    expect(result.current).toBe(false);
  });

  it("compacts once an attributed scroller passes the enter threshold", () => {
    const { result } = renderAt("/discover");
    dispatchScroll(200, true);
    expect(result.current).toBe(true);
  });

  it("ignores scroll from an element without the page-scroll attribute", () => {
    const { result } = renderAt("/discover");
    dispatchScroll(200, false);
    expect(result.current).toBe(false);
  });

  it("does not compact while inside the hysteresis band", () => {
    const { result } = renderAt("/discover");
    dispatchScroll(40, true);
    expect(result.current).toBe(false);
  });

  it("stays compact while inside the hysteresis band once compacted", () => {
    const { result } = renderAt("/discover");
    dispatchScroll(200, true);
    dispatchScroll(40, true);
    expect(result.current).toBe(true);
  });

  it("expands again once scrolled below the exit threshold", () => {
    const { result } = renderAt("/discover");
    dispatchScroll(200, true);
    dispatchScroll(10, true);
    expect(result.current).toBe(false);
  });
});
