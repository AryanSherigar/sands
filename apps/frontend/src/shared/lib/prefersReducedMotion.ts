import { REDUCED_MOTION_MEDIA_QUERY } from "@/shared/constants/reader-preferences";

export const prefersReducedMotion = (): boolean =>
  typeof window !== "undefined" &&
  Boolean(window.matchMedia?.(REDUCED_MOTION_MEDIA_QUERY).matches);
