import type { EndingGrade, EndingState } from "../types/simulation.types";

export interface EndingDescription {
  headline: string;
  summary: string;
  gradeLabel: string | null;
}

const KNOWN_ENDINGS: Record<string, { headline: string; summary: string }> = {
  default_victory_conquest: {
    headline: "Conquest",
    summary: "Every rival capital is yours. No court is left to oppose you.",
  },
  default_victory_hegemony: {
    headline: "Hegemony",
    summary: "Your realm holds so much of the land that none can challenge it.",
  },
  default_defeat_capital_lost: {
    headline: "The Capital Falls",
    summary: "Your seat of power is in enemy hands, and the realm falls with it.",
  },
  default_defeat_revolution: {
    headline: "Revolution",
    summary: "Unrest went unanswered for too long, and the crown was overthrown.",
  },
  default_defeat_regime_fall: {
    headline: "The Regime Falls",
    summary: "Your rule has collapsed.",
  },
  default_graded_negotiated_peace: {
    headline: "A Negotiated Peace",
    summary: "The wars ended at the table. History will weigh what you kept.",
  },
  default_graded_end_date: {
    headline: "The Campaign Ends",
    summary: "The years allotted to your reign have run out.",
  },
  default_graded_vassal_state: {
    headline: "A Vassal State",
    summary: "Your realm survives under a greater crown.",
  },
};

const GRADE_LABELS: Record<EndingGrade, string> = {
  triumph: "Triumph",
  honorable: "Honorable",
  pyrrhic: "Pyrrhic",
  bitter: "Bitter",
  ruin: "Ruin",
};

const KIND_FALLBACK: Record<string, string> = {
  victory: "Victory",
  defeat: "Defeat",
  graded: "The Campaign Ends",
};

const INPUT_LABELS: Record<string, string> = {
  position: "Land held",
  stability: "Stability",
  treasury: "Treasury",
  will: "Will to fight",
  strain: "Strain borne",
};

const titleCase = (text: string): string =>
  text.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());

export function describeEnding(ending: EndingState): EndingDescription {
  const known = KNOWN_ENDINGS[ending.ending_id];
  return {
    headline: known?.headline ?? KIND_FALLBACK[ending.kind] ?? titleCase(ending.ending_id),
    summary: known?.summary ?? "",
    gradeLabel: ending.grade ? GRADE_LABELS[ending.grade] : null,
  };
}

export const describeEndingInput = (key: string): string => INPUT_LABELS[key] ?? titleCase(key);
