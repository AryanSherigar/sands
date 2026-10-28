import { ClockGlitch } from "@/shared/types/display-hints.types";
import { seededUnit } from "./seededUnit";

const FIRST_IMPOSSIBLE_MINUTE = 60;
const IMPOSSIBLE_MINUTE_SPAN = 40;
const MINUTE_SEED_SUFFIX = "minute";

export interface GlitchedClockInput {
  playthroughId: string;
  displayedMinutes: number;
  glitch: ClockGlitch | undefined;
  sourceValue: unknown;
}

// An impossible minute value (60-99) for the clock to show, or null. The draw
// is seeded by the playthrough and the displayed minute, so a given minute
// always renders the same way and never flickers between renders.
export function glitchedClock({
  playthroughId,
  displayedMinutes,
  glitch,
  sourceValue,
}: GlitchedClockInput): number | null {
  if (!glitch || typeof sourceValue !== "number") return null;
  if (sourceValue >= glitch.below) return null;
  if (seededUnit(playthroughId, displayedMinutes) >= glitch.chance) return null;
  const unit = seededUnit(`${playthroughId}:${MINUTE_SEED_SUFFIX}`, displayedMinutes);
  return FIRST_IMPOSSIBLE_MINUTE + Math.floor(unit * IMPOSSIBLE_MINUTE_SPAN);
}
