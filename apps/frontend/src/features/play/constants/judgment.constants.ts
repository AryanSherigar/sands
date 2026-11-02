import type {
  JudgmentNuanceId,
  JudgmentStance,
  JudgmentVerdictId,
} from "../types/judgmentScene.types";

export const JUDGMENT_SCENE_TYPE = "judgment";
export const DEFAULT_JUDGMENT_VERDICT: JudgmentVerdictId = "imprison";
export const JUDGMENT_SPOKEN_MAX_CHARS = 600;
export const JUDGMENT_DECREE_MAX_CHARS = 1200;
export const JUDGMENT_CHARGE_FACT_LABEL = "Charge";
export const JUDGMENT_FALLBACK_CHARGE = "Awaiting the sovereign's word";
export const JUDGMENT_CONVENING_MESSAGE = "The court is being convened.";
export const JUDGMENT_NO_APPEAL_LABEL = "No right of appeal";

export interface JudgmentNuanceDefinition {
  id: JudgmentNuanceId;
  label: string;
}

export interface JudgmentVerdictDefinition {
  id: JudgmentVerdictId;
  label: string;
  tagline: string;
  icon: string;
  shortcut: string;
  nuances: readonly JudgmentNuanceDefinition[];
}

export const JUDGMENT_VERDICTS: readonly JudgmentVerdictDefinition[] = [
  {
    id: "release",
    label: "Release",
    tagline: "Lenient clemency",
    icon: "lock_open_right",
    shortcut: "1",
    nuances: [
      { id: "with_warning", label: "with a warning" },
      { id: "under_oath", label: "under oath" },
      { id: "with_pardon", label: "with a pardon" },
      { id: "with_fine", label: "with a fine" },
    ],
  },
  {
    id: "exile",
    label: "Exile",
    tagline: "Banish from realms",
    icon: "sailing",
    shortcut: "2",
    nuances: [
      { id: "beyond_border", label: "beyond the border" },
      { id: "stripped_of_title", label: "stripped of title" },
      { id: "with_family", label: "with family" },
      { id: "with_price_on_return", label: "with a price on return" },
    ],
  },
  {
    id: "imprison",
    label: "Imprison",
    tagline: "Kept in chains",
    icon: "fort",
    shortcut: "3",
    nuances: [
      { id: "in_region", label: "in the region" },
      { id: "in_capital", label: "in the capital" },
      { id: "for_a_term", label: "for a term" },
      { id: "for_life", label: "for life" },
    ],
  },
  {
    id: "execute",
    label: "Execute",
    tagline: "The headsman's axe",
    icon: "swords",
    shortcut: "4",
    nuances: [
      { id: "quietly", label: "quietly" },
      { id: "publicly", label: "publicly" },
      { id: "swiftly", label: "swiftly" },
      { id: "with_last_word", label: "with a last word" },
    ],
  },
];

export const JUDGMENT_WHISPERS: readonly string[] = [
  "Your title is forfeit, but your blood remains your own.",
  "Kneel before this court and swear fealty.",
  "Let the realm see what becomes of those who raise arms against it.",
];

export interface JudgmentStanceDefinition {
  label: string;
  icon: string;
}

export const JUDGMENT_STANCES: Readonly<Record<JudgmentStance, JudgmentStanceDefinition>> = {
  mercy: { label: "Urges mercy", icon: "volunteer_activism" },
  iron: { label: "Iron example", icon: "shield" },
  neutral: { label: "Weighs both", icon: "balance" },
};

export const JUDGMENT_SPEAK_FAILED_MESSAGE = "The court could not be heard. Try again.";
