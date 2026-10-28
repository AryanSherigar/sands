// Mirrors apps/core-api/app/models/sheet_rule.py: the engine owns a rule's status
// in hidden state, and the browser only ever receives rules that are no longer
// `unrevealed`, so the unrevealed status is not part of what the client sees.
export const RULE_STATUSES = [
  "intact",
  "active_threat",
  "violated",
  "corrupted",
] as const;

export type RuleStatus = (typeof RULE_STATUSES)[number];

export const RULE_HANDS = [
  "typed",
  "pencil",
  "ink",
  "printed",
  "spoken",
  "ink_block",
] as const;

export type RuleHand = (typeof RULE_HANDS)[number];

export interface RuleSheetItem {
  key: string;
  number: number;
  text: string;
  status: RuleStatus;
  source_style: RuleHand;
}
