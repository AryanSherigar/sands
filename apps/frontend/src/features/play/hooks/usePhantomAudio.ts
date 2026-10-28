import { useEffect } from "react";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { usePlayStore } from "../stores/play.store";
import { useSanityBand } from "./useSanityBand";

// Turns the faint phantom whispers on while sanity is under the meter's
// `moderate_below` threshold. `useSanityBand` is already off when the reader
// reduces sensory effects or the tools are not on.
export function usePhantomAudio(): void {
  const { band } = useSanityBand();
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id ?? "");
  const isHaunted = band !== "none";

  useEffect(() => {
    if (!isHaunted) return undefined;
    ambientSoundtrack.setPhantomAmbience(1, playthroughId);
    return () => ambientSoundtrack.setPhantomAmbience(0);
  }, [isHaunted, playthroughId]);
}
