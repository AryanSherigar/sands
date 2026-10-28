import { ScenarioMood } from "@/shared/types/audio.types";

/** Safety net for pre-migration playthrough snapshots that permanently
 * pinned a literal null; the backend otherwise always resolves a real URL
 * (built-in default or a creator's custom track) for every mood. */
export function getMoodTrackUrl(
  mood: ScenarioMood,
  tracks: Partial<Record<ScenarioMood, string | null>> | undefined,
): string | undefined {
  return tracks?.[mood] ?? undefined;
}

// Must equal MOOD_SLOTS in apps/core-api/app/db/models/scenario_music.py.
export const SCENARIO_MOODS: readonly ScenarioMood[] = [
  "peaceful",
  "mystery",
  "tension",
  "combat",
  "melancholy",
  "triumph",
];
