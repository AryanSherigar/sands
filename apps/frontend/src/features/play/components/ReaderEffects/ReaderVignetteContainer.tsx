import { ReaderVignette } from "@/shared/components/reader-effects/ReaderVignette";
import { tensionVignetteStrength } from "@/shared/lib/hud/tensionVignette";
import { usePlayStore } from "../../stores/play.store";
import { useTensionTier } from "../../hooks/useTensionTier";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";

/**
 * The tension vignette. Renders only for a scenario with Atmosphere and Status
 * HUD on and a tier field to read; stays on screen (static) when the reader
 * reduces sensory effects.
 */
export function ReaderVignetteContainer() {
  const tension = useTensionTier();
  const theme = usePlayStore((s) => s.ebook_theme);
  const isMotionReduced = useIsMotionReduced();

  if (!tension) return null;

  return (
    <ReaderVignette
      strength={tensionVignetteStrength(tension.index, tension.count)}
      theme={theme}
      shouldAnimate={!isMotionReduced}
    />
  );
}
