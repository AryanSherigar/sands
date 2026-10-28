import { useEffect } from "react";
import { getMoodTrackUrl } from "@/shared/constants/audio";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { ScenarioMood } from "@/shared/types/audio.types";
import { whenCuesIdle } from "../lib/atmosphereSubscriber";
import { usePlayStore } from "../stores/play.store";
import { useTensionTier } from "./useTensionTier";

export const TIER_CROSSFADE_SECONDS = 1.5;
const SCENARIO_MOODS: readonly string[] = [
  "peaceful",
  "mystery",
  "tension",
  "combat",
  "melancholy",
  "triumph",
];

const isScenarioMood = (value: string | undefined): value is ScenarioMood =>
  value !== undefined && SCENARIO_MOODS.includes(value);

// Moves the ambient track with the tension tier through the forced fast path
// (no cooldown, 1.5 s fade), including once on mount so a reload mid-story
// resumes the right track. The tier's own track wins; the `mood_map` mood
// track is both the choice for a tier without one and the fallback when the
// tier's file fails to load. A change that arrives during a cue waits until
// the ambience is back. Does nothing without a `mood_map`.
export function useTierAudio(): void {
  const tension = useTensionTier();
  const musicTracks = usePlayStore((s) => s.playthrough?.music_tracks);
  const tierTracks = usePlayStore((s) => s.playthrough?.tier_tracks);
  const mappedMood = tension?.moodMap?.[tension.value];
  const mood = isScenarioMood(mappedMood) ? mappedMood : null;
  const moodTrackUrl = mood ? getMoodTrackUrl(mood, musicTracks) : undefined;
  const tierTrackUrl = tension ? tierTracks?.[tension.value] : undefined;
  const trackUrl = tierTrackUrl ?? moodTrackUrl;

  useEffect(() => {
    if (!mood) return undefined;
    let isStale = false;
    void whenCuesIdle().then(() => {
      if (isStale) return;
      ambientSoundtrack.transitionTo(mood, trackUrl, {
        isForce: true,
        crossfadeSeconds: TIER_CROSSFADE_SECONDS,
        fallbackUrl: moodTrackUrl,
      });
    });
    return () => {
      isStale = true;
    };
  }, [mood, trackUrl, moodTrackUrl]);
}
