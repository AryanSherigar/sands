import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAlphaSession } from "../useAlphaSession";
import { emitAlphaEvent, flushAlphaEventsOnHide } from "@/shared/lib/alpha-events";
import { recordUiUsed, drainSessionStats } from "@/shared/lib/alpha-session-stats";

vi.mock("@/shared/lib/alpha-events", () => ({
  emitAlphaEvent: vi.fn(),
  flushAlphaEventsOnHide: vi.fn(),
}));

const DESKTOP_WIDTH_PX = 1280;

function emittedNames(): string[] {
  return vi.mocked(emitAlphaEvent).mock.calls.map((call) => call[0]);
}

describe("useAlphaSession", () => {
  beforeEach(() => {
    vi.mocked(emitAlphaEvent).mockClear();
    vi.mocked(flushAlphaEventsOnHide).mockClear();
    drainSessionStats();
    window.innerWidth = DESKTOP_WIDTH_PX;
  });

  it("emits nothing while collection is off", () => {
    renderHook(() => useAlphaSession(false));
    window.dispatchEvent(new Event("pagehide"));

    expect(emitAlphaEvent).not.toHaveBeenCalled();
  });

  it("starts a session with device info and no personal strings", () => {
    renderHook(() => useAlphaSession(true));

    expect(emittedNames()).toEqual(["session_start", "device_info"]);
    const deviceInfo = vi.mocked(emitAlphaEvent).mock.calls[1][1];
    expect(deviceInfo).toMatchObject({
      device_class: "desktop",
      viewport_bucket: "lg",
    });
    expect(JSON.stringify(deviceInfo)).not.toMatch(/Mozilla|jsdom/);
  });

  it("ends the session on page hide, with ui use, and flushes", () => {
    renderHook(() => useAlphaSession(true));
    vi.mocked(emitAlphaEvent).mockClear();
    recordUiUsed("map");

    window.dispatchEvent(new Event("pagehide"));

    expect(emittedNames()).toEqual(["ui_used", "session_end"]);
    expect(flushAlphaEventsOnHide).toHaveBeenCalledTimes(1);
  });

  it("flushes when the tab becomes hidden", () => {
    renderHook(() => useAlphaSession(true));
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });

    document.dispatchEvent(new Event("visibilitychange"));

    expect(flushAlphaEventsOnHide).toHaveBeenCalledTimes(1);
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
  });
});
