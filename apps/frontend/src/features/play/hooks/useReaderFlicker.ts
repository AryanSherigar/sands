import { useEffect, useRef, useState } from "react";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { useAtmosphereStore } from "../stores/atmosphere.store";
import { useTensionTier } from "./useTensionTier";

export const POWER_FLICKER_MS = 250;

// True for a short moment after a power cut (a cue that cuts the ambience) or a
// rise in the tension tier. Never fires on mount or reload, and never when the
// reader reduces sensory effects.
export function useReaderFlicker(): boolean {
  const flickerNonce = useAtmosphereStore((s) => s.flickerNonce);
  const triggerFlicker = useAtmosphereStore((s) => s.triggerFlicker);
  const shouldReduce = useReaderPreferencesStore((s) => s.reduceSensoryEffects);
  const tierIndex = useTensionTier()?.index ?? null;
  const [isFlickering, setIsFlickering] = useState(false);
  const previousTierIndex = useRef(tierIndex);
  const lastSeenNonce = useRef(flickerNonce);

  useEffect(() => {
    const previous = previousTierIndex.current;
    previousTierIndex.current = tierIndex;
    if (previous !== null && tierIndex !== null && tierIndex > previous) {
      triggerFlicker();
    }
  }, [tierIndex, triggerFlicker]);

  useEffect(() => {
    if (flickerNonce === lastSeenNonce.current) return undefined;
    lastSeenNonce.current = flickerNonce;
    if (shouldReduce) return undefined;
    setIsFlickering(true);
    const timer = setTimeout(() => setIsFlickering(false), POWER_FLICKER_MS);
    return () => clearTimeout(timer);
  }, [flickerNonce, shouldReduce]);

  return isFlickering;
}
