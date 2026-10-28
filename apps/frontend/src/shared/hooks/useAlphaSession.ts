import { useEffect } from "react";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { emitAlphaEvent, flushAlphaEventsOnHide } from "@/shared/lib/alpha-events";
import {
  bucketViewport,
  browserFamilyOf,
  classifyDevice,
} from "@/shared/lib/alpha-device-info";
import {
  createVisibilityTracker,
  drainSessionStats,
} from "@/shared/lib/alpha-session-stats";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { DeviceInfoProps } from "@/shared/types/alphaEvents.types";

function readDeviceInfo(): DeviceInfoProps {
  const widthPx = window.innerWidth;
  return {
    device_class: classifyDevice(widthPx),
    viewport_bucket: bucketViewport(widthPx),
    browser_family: browserFamilyOf(navigator.userAgent),
    is_reduce_effects_on: useReaderPreferencesStore.getState().reduceSensoryEffects,
    is_audio_muted: ambientSoundtrack.getIsMuted(),
  };
}

export function useAlphaSession(isCollecting: boolean): void {
  useEffect(() => {
    if (!isCollecting) return;
    const tracker = createVisibilityTracker(document.visibilityState);
    emitAlphaEvent("session_start", {
      visible_ms: 0,
      hidden_ms: 0,
      sfx_played_count: 0,
      audio_blocked_count: 0,
    });
    emitAlphaEvent("device_info", readDeviceInfo());

    const handleVisibilityChange = (): void => {
      tracker.update(document.visibilityState);
      if (document.visibilityState === "hidden") flushAlphaEventsOnHide();
    };
    const handlePageHide = (): void => {
      const { counters, uiUse } = drainSessionStats();
      uiUse.forEach(([feature, count]) =>
        emitAlphaEvent("ui_used", { feature, count }),
      );
      emitAlphaEvent("session_end", {
        ...tracker.snapshot(),
        turns_in_session: counters.turns_in_session,
        sfx_played_count: counters.sfx_played_count,
        audio_blocked_count: counters.audio_blocked_count,
      });
      flushAlphaEventsOnHide();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [isCollecting]);
}
