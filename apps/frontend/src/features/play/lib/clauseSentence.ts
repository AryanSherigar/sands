export type ClauseTemplate =
  | "treasury_below"
  | "treasury_above"
  | "stability_below"
  | "war_exhaustion_above"
  | "region_count_below"
  | "region_count_above"
  | "turn_after"
  | "owns_region"
  | "loses_region";

export type ClauseKind =
  | "payment"
  | "tribute"
  | "pact"
  | "trade_deal"
  | "military_access"
  | "promise"
  | "cede_region"
  | "region_promise";
export type ClauseMode = "none" | "trigger" | "gate";
export type ClauseSubject = "mine" | "yours";

export interface ClauseDraft {
  mode: ClauseMode;
  kind: ClauseKind;
  amount: number;
  template: ClauseTemplate;
  subject: ClauseSubject;
  value: number;
  expiresInTurns: number;
  regionId?: string;
  regionName?: string;
}

export const MIN_EXPIRY_TURNS = 1;
export const MAX_EXPIRY_TURNS = 40;

export const TEMPLATE_LABELS: Record<ClauseTemplate, string> = {
  treasury_below: "a treasury falls below",
  treasury_above: "a treasury rises above",
  stability_below: "stability falls below",
  war_exhaustion_above: "war exhaustion rises above",
  region_count_below: "a realm holds fewer regions than",
  region_count_above: "a realm holds more regions than",
  turn_after: "this turn has passed:",
  owns_region: "a realm holds the region",
  loses_region: "a realm no longer holds the region",
};

export const REGION_TEMPLATES: ClauseTemplate[] = ["owns_region", "loses_region"];
export const REGION_KINDS: ClauseKind[] = ["cede_region", "region_promise"];

export const isRegionTemplate = (template: ClauseTemplate): boolean =>
  REGION_TEMPLATES.includes(template);
export const isRegionKind = (kind: ClauseKind): boolean => REGION_KINDS.includes(kind);

export const KIND_LABELS: Record<ClauseKind, string> = {
  payment: "A payment of gold",
  tribute: "Tribute (a share of income)",
  pact: "A non-aggression pact",
  trade_deal: "A trade deal",
  military_access: "Military access",
  promise: "A promise never to attack",
  cede_region: "Handing over a region",
  region_promise: "A promise never to occupy a region",
};

// NOTE: a gate keeps an ongoing clause in force only while the condition holds, so it can only wrap clauses that continue.
export const GATE_KINDS: ClauseKind[] = [
  "tribute",
  "pact",
  "trade_deal",
  "military_access",
  "promise",
  "region_promise",
];

const SUBJECT_WORDS: Record<ClauseSubject, string> = { mine: "my", yours: "your" };

const CONDITION_TEXT: Record<ClauseTemplate, (subject: string, value: number, region: string) => string> = {
  treasury_below: (subject, value) => `${subject} treasury is below ${value} gold`,
  treasury_above: (subject, value) => `${subject} treasury is above ${value} gold`,
  stability_below: (subject, value) => `${subject} stability is below ${value}`,
  war_exhaustion_above: (subject, value) => `${subject} war exhaustion is above ${value}`,
  region_count_below: (subject, value) => `${subject} realm holds fewer than ${value} regions`,
  region_count_above: (subject, value) => `${subject} realm holds more than ${value} regions`,
  turn_after: (_subject, value) => `turn ${value} has passed`,
  owns_region: (subject, _value, region) => `${subject} realm holds ${region}`,
  loses_region: (subject, _value, region) => `${subject} realm no longer holds ${region}`,
};

const CLAUSE_TEXT: Record<ClauseKind, (amount: number, region: string) => string> = {
  payment: (amount) => `I will pay you ${amount} gold`,
  tribute: (amount) => `I will pay you ${amount}% of my income as tribute`,
  pact: (amount) => `we will keep a non-aggression pact for ${amount} turns`,
  trade_deal: () => "we will keep a trade deal",
  military_access: () => "I will grant you military access through my lands",
  promise: () => "I swear never to attack you",
  cede_region: (_amount, region) => `I will hand ${region} over to you`,
  region_promise: (_amount, region) => `I swear never to occupy ${region}`,
};

const clampTurns = (turns: number): number =>
  Math.max(MIN_EXPIRY_TURNS, Math.min(MAX_EXPIRY_TURNS, Math.round(turns)));

const FALLBACK_REGION = "that region";

export function composeClauseSentence(draft: ClauseDraft): string {
  const region = draft.regionName ?? FALLBACK_REGION;
  const clause = CLAUSE_TEXT[draft.kind](draft.amount, region);
  if (draft.mode === "none") return `${capitalize(clause)}.`;
  const condition = CONDITION_TEXT[draft.template](SUBJECT_WORDS[draft.subject], draft.value, region);
  const opening = draft.mode === "trigger" ? `Once ${condition}, ${clause}.` : `${capitalize(clause)}, but only while ${condition}.`;
  const turns = clampTurns(draft.expiresInTurns);
  return `${opening} Let this agreement lapse after ${turns} ${turns === 1 ? "turn" : "turns"}.`;
}

export const composeCardSentence = (drafts: ClauseDraft[]): string =>
  drafts.map(composeClauseSentence).join(" ");

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
