export type ClauseTemplate =
  | "treasury_below"
  | "treasury_above"
  | "stability_below"
  | "war_exhaustion_above"
  | "region_count_below"
  | "region_count_above"
  | "turn_after";

export type ClauseKind = "payment" | "tribute" | "pact" | "trade_deal" | "military_access" | "promise";
export type ClauseMode = "trigger" | "gate";
export type ClauseSubject = "mine" | "yours";

export interface ClauseDraft {
  mode: ClauseMode;
  kind: ClauseKind;
  amount: number;
  template: ClauseTemplate;
  subject: ClauseSubject;
  value: number;
  expiresInTurns: number;
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
};

export const KIND_LABELS: Record<ClauseKind, string> = {
  payment: "A payment of gold",
  tribute: "Tribute (a share of income)",
  pact: "A non-aggression pact",
  trade_deal: "A trade deal",
  military_access: "Military access",
  promise: "A promise never to attack",
};

// NOTE: a gate keeps an ongoing clause in force only while the condition holds, so it can only wrap clauses that continue.
export const GATE_KINDS: ClauseKind[] = ["tribute", "pact", "trade_deal", "military_access", "promise"];

const SUBJECT_WORDS: Record<ClauseSubject, string> = { mine: "my", yours: "your" };

const CONDITION_TEXT: Record<ClauseTemplate, (subject: string, value: number) => string> = {
  treasury_below: (subject, value) => `${subject} treasury is below ${value} gold`,
  treasury_above: (subject, value) => `${subject} treasury is above ${value} gold`,
  stability_below: (subject, value) => `${subject} stability is below ${value}`,
  war_exhaustion_above: (subject, value) => `${subject} war exhaustion is above ${value}`,
  region_count_below: (subject, value) => `${subject} realm holds fewer than ${value} regions`,
  region_count_above: (subject, value) => `${subject} realm holds more than ${value} regions`,
  turn_after: (_subject, value) => `turn ${value} has passed`,
};

const CLAUSE_TEXT: Record<ClauseKind, (amount: number) => string> = {
  payment: (amount) => `I will pay you ${amount} gold`,
  tribute: (amount) => `I will pay you ${amount}% of my income as tribute`,
  pact: (amount) => `we will keep a non-aggression pact for ${amount} turns`,
  trade_deal: () => "we will keep a trade deal",
  military_access: () => "I will grant you military access through my lands",
  promise: () => "I swear never to attack you",
};

const clampTurns = (turns: number): number =>
  Math.max(MIN_EXPIRY_TURNS, Math.min(MAX_EXPIRY_TURNS, Math.round(turns)));

export function composeClauseSentence(draft: ClauseDraft): string {
  const condition = CONDITION_TEXT[draft.template](SUBJECT_WORDS[draft.subject], draft.value);
  const clause = CLAUSE_TEXT[draft.kind](draft.amount);
  const opening = draft.mode === "trigger" ? `Once ${condition}, ${clause}.` : `${capitalize(clause)}, but only while ${condition}.`;
  const turns = clampTurns(draft.expiresInTurns);
  return `${opening} Let this agreement lapse after ${turns} ${turns === 1 ? "turn" : "turns"}.`;
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
