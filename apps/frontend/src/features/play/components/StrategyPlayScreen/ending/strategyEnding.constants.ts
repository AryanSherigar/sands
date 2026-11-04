import type { EndingView } from "../../../types/simulation.types";

export const ENDING_TIER_LABELS: Record<string, string> = {
  triumph: "Triumph",
  honorable: "Honorable",
  pyrrhic: "Pyrrhic Victory",
  bitter: "Bitter",
  ruin: "Ruin",
};

const VICTORY_TIER = "triumph";
const DEFEAT_TIER = "ruin";
const GRADED_FALLBACK_TIER = "honorable";

export const ENDING_FALLBACK_TITLE = "The Reign Ends";

export const ENDING_TITLES: Record<string, string> = {
  default_defeat_capital_lost: "The Capital Falls",
  default_defeat_revolution: "The Crown Is Overthrown",
  default_defeat_regime_fall: "The Regime Falls",
  default_victory_conquest: "The Realm Is Won",
  default_victory_hegemony: "A Hegemon Rises",
  default_graded_negotiated_peace: "A Peace That Holds",
  default_graded_end_date: "The Reign Reaches Its End",
  default_graded_vassal_state: "A Vassal's Crown",
};

export function getEndingTitle(endingId: string, authoredName?: string): string {
  return authoredName || (ENDING_TITLES[endingId] ?? ENDING_FALLBACK_TITLE);
}

export function getEndingTierLabel(ending: EndingView): string {
  if (ending.grade && ENDING_TIER_LABELS[ending.grade]) return ENDING_TIER_LABELS[ending.grade];
  if (ending.kind === "victory") return ENDING_TIER_LABELS[VICTORY_TIER];
  if (ending.kind === "defeat") return ENDING_TIER_LABELS[DEFEAT_TIER];
  return ENDING_TIER_LABELS[GRADED_FALLBACK_TIER];
}
