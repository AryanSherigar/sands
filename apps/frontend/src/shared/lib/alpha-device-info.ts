import {
  BROWSER_FAMILY_OTHER,
  BROWSER_FAMILY_PATTERNS,
  VIEWPORT_BUCKETS,
  VIEWPORT_LARGEST_BUCKET,
  VIEWPORT_PHONE_MAX_PX,
  VIEWPORT_TABLET_MAX_PX,
} from "@/shared/constants/alpha-events";
import type { DeviceInfoProps } from "@/shared/types/alphaEvents.types";

export function classifyDevice(widthPx: number): DeviceInfoProps["device_class"] {
  if (widthPx < VIEWPORT_PHONE_MAX_PX) return "phone";
  if (widthPx < VIEWPORT_TABLET_MAX_PX) return "tablet";
  return "desktop";
}

export function bucketViewport(widthPx: number): string {
  const found = VIEWPORT_BUCKETS.find(([, maxPx]) => widthPx < maxPx);
  return found ? found[0] : VIEWPORT_LARGEST_BUCKET;
}

export function browserFamilyOf(userAgent: string): string {
  const found = BROWSER_FAMILY_PATTERNS.find(([, pattern]) =>
    pattern.test(userAgent),
  );
  return found ? found[0] : BROWSER_FAMILY_OTHER;
}
