import { REDUCED_MOTION_MEDIA_QUERY } from "@/shared/constants/reader-preferences";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useMediaQuery } from "./useMediaQuery";

// True when the reader switched on "Reduce sensory effects" or the OS asks for
// reduced motion. Effects check this before animating.
export function useIsMotionReduced(): boolean {
  const reduceSensoryEffects = useReaderPreferencesStore(
    (s) => s.reduceSensoryEffects,
  );
  const prefersReducedMotion = useMediaQuery(REDUCED_MOTION_MEDIA_QUERY);
  return reduceSensoryEffects || prefersReducedMotion;
}
