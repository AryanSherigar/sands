import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import {
  CANONICAL_GREY_LEDGER,
  CANONICAL_SUBSTRATUM,
  CANONICAL_OAKHAVEN,
} from "../constants/canonicalScenarios.constants";

export interface PlaythroughDisplayInfo {
  genre: string;
  author: string;
  excerpt: string;
}

const CANONICAL_MAP: Record<string, PlaythroughDisplayInfo> = {
  [CANONICAL_GREY_LEDGER.title]: {
    genre: "Noir / Detective",
    author: "M. E. Holloway",
    excerpt:
      "The dockmaster's ledger had three names scratched out in fresh ink. Rain tapped against your trench coat as footsteps echoed from Pier 9.",
  },
  [CANONICAL_SUBSTRATUM.title]: {
    genre: "Sci-Fi",
    author: "Vance Thorne",
    excerpt:
      "Air pressure in Sector 4 dropped to 0.4 atm. The auxiliary geothermal valve responded, but thermal telemetry showed rising coolant levels.",
  },
  [CANONICAL_OAKHAVEN.title]: {
    genre: "High Fantasy",
    author: "Linchpin Canon",
    excerpt:
      "In a dying realm where written history turns to ash, you guard the final repository of forbidden knowledge. Every vow you break alters the world.",
  },
};

export const resolvePlaythroughDisplay = (
  playthrough: UserPlaythroughSummary,
): PlaythroughDisplayInfo => {
  const match = CANONICAL_MAP[playthrough.scenario_title];
  if (match) return match;

  const genre = playthrough.scenario_mode === "master" ? "Advanced" : "Simple";
  const author = playthrough.character_name
    ? `as ${playthrough.character_name}`
    : "by Author";
  const excerpt =
    playthrough.ended_outcome_text ??
    "Your journey through the narrative is paused. Return to shape the next chapter.";

  return { genre, author, excerpt };
};
