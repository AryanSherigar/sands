import type { RuleHand, RuleStatus } from "@/shared/types/rule-sheet.types";

// Must equal INITIAL_STATUSES in apps/core-api/app/models/sheet_rule.py;
// apps/core-api/tests/test_frontend_constants_drift.py parses this array.
export const INITIAL_STATUSES = ["unrevealed", "intact"] as const;

export type InitialRuleStatus = (typeof INITIAL_STATUSES)[number];

export const HAND_LABELS: Record<RuleHand, string> = {
  typed: "Typed",
  pencil: "Pencil",
  ink: "Blue ink",
  printed: "Printed",
  spoken: "Spoken",
  ink_block: "Blue ink (upright, separate letters)",
};

export const STATUS_LABELS: Record<RuleStatus | "unrevealed", string> = {
  unrevealed: "Not shown yet",
  intact: "Intact",
  active_threat: "Active threat",
  violated: "Violated",
  corrupted: "Corrupted",
};

export const MAX_RULE_TEXT_LENGTH = 600;
export const MAX_RULE_NUMBER = 99;
export const RULE_KEY_PATTERN = /^[a-z][a-z0-9_]{0,30}$/;
