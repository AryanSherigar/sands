import { DEFAULT_STRATEGY_RULES, MAX_CONDITIONAL_PERCENT } from "../constants/strategyAuthoring";
import type { StrategyFields, StrategyRules } from "../types/strategyDocument.types";
import { clampWholeNumber } from "./strategyStart";

type RawBlock = Record<string, unknown>;

const MIN_POSITIVE = 1;
const POSITIVE_RULES: readonly (keyof StrategyRules)[] = [
  "trade_value_per_turn",
  "trade_income_percent",
  "access_value_per_turn",
  "oath_offer_duration_turns",
  "letter_cooldown_turns",
  "judgment_cooldown_turns",
  "judgment_sentence_turns",
];
const PERCENT_RULES: readonly (keyof StrategyRules)[] = ["conditional_trigger_percent", "conditional_gate_percent"];

const asBlock = (value: unknown): RawBlock =>
  value !== null && typeof value === "object" ? (value as RawBlock) : {};

const numberOr = (value: unknown, fallback: number): number =>
  typeof value === "number" && Number.isFinite(value) ? value : fallback;

export const readRules = (tuning: RawBlock): StrategyRules => {
  const agents = asBlock(tuning.agents);
  const treaty = asBlock(tuning.treaty);
  const overtures = asBlock(tuning.overtures);
  const revoltTalk = asBlock(tuning.revolt_talk);
  const letters = asBlock(tuning.letters);
  const judgments = asBlock(tuning.judgments);
  const defaults = DEFAULT_STRATEGY_RULES;
  return {
    agents_enabled: agents.is_enabled === true,
    revolt_talks_enabled: revoltTalk.is_enabled === true,
    bribe_base_price: numberOr(agents.bribe_base_price, defaults.bribe_base_price),
    trade_value_per_turn: numberOr(treaty.trade_value_per_turn, defaults.trade_value_per_turn),
    trade_income_percent: numberOr(treaty.trade_income_percent, defaults.trade_income_percent),
    access_value_per_turn: numberOr(treaty.access_value_per_turn, defaults.access_value_per_turn),
    conditional_trigger_percent: numberOr(treaty.conditional_trigger_percent, defaults.conditional_trigger_percent),
    conditional_gate_percent: numberOr(treaty.conditional_gate_percent, defaults.conditional_gate_percent),
    oath_offer_min_opinion: numberOr(overtures.oath_offer_min_opinion, defaults.oath_offer_min_opinion),
    oath_offer_duration_turns: numberOr(overtures.oath_offer_duration_turns, defaults.oath_offer_duration_turns),
    letters_enabled: letters.is_enabled === true,
    letter_cooldown_turns: numberOr(letters.cooldown_turns, defaults.letter_cooldown_turns),
    judgments_enabled: judgments.is_enabled === true,
    judgment_cooldown_turns: numberOr(judgments.cooldown_turns, defaults.judgment_cooldown_turns),
    judgment_sentence_turns: numberOr(judgments.sentence_turns, defaults.judgment_sentence_turns),
  };
};

interface RuleLocation {
  block: "agents" | "treaty" | "overtures" | "revolt_talk" | "letters" | "judgments";
  field: string;
}

const RULE_LOCATIONS: Record<keyof StrategyRules, RuleLocation> = {
  agents_enabled: { block: "agents", field: "is_enabled" },
  revolt_talks_enabled: { block: "revolt_talk", field: "is_enabled" },
  bribe_base_price: { block: "agents", field: "bribe_base_price" },
  trade_value_per_turn: { block: "treaty", field: "trade_value_per_turn" },
  trade_income_percent: { block: "treaty", field: "trade_income_percent" },
  access_value_per_turn: { block: "treaty", field: "access_value_per_turn" },
  conditional_trigger_percent: { block: "treaty", field: "conditional_trigger_percent" },
  conditional_gate_percent: { block: "treaty", field: "conditional_gate_percent" },
  oath_offer_min_opinion: { block: "overtures", field: "oath_offer_min_opinion" },
  oath_offer_duration_turns: { block: "overtures", field: "oath_offer_duration_turns" },
  letters_enabled: { block: "letters", field: "is_enabled" },
  letter_cooldown_turns: { block: "letters", field: "cooldown_turns" },
  judgments_enabled: { block: "judgments", field: "is_enabled" },
  judgment_cooldown_turns: { block: "judgments", field: "cooldown_turns" },
  judgment_sentence_turns: { block: "judgments", field: "sentence_turns" },
};

// NOTE: only changed rules are written, so an untouched document is never rewritten with defaults.
export const applyRules = (tuning: RawBlock, rules: StrategyRules): RawBlock => {
  const current = readRules(tuning);
  const next: RawBlock = { ...tuning };
  for (const key of Object.keys(RULE_LOCATIONS) as (keyof StrategyRules)[]) {
    if (rules[key] === current[key]) continue;
    const { block, field } = RULE_LOCATIONS[key];
    next[block] = { ...asBlock(next[block]), [field]: rules[key] };
  }
  return next;
};

const normalize = (rules: StrategyRules): StrategyRules => {
  const next = { ...rules };
  for (const key of POSITIVE_RULES) {
    (next[key] as number) = Math.max(MIN_POSITIVE, clampWholeNumber(rules[key] as number));
  }
  for (const key of PERCENT_RULES) {
    (next[key] as number) = clampWholeNumber(rules[key] as number, MAX_CONDITIONAL_PERCENT);
  }
  next.bribe_base_price = clampWholeNumber(rules.bribe_base_price);
  next.oath_offer_min_opinion = clampWholeNumber(rules.oath_offer_min_opinion);
  return next;
};

export const setRules = (fields: StrategyFields, patch: Partial<StrategyRules>): StrategyFields => ({
  ...fields,
  rules: normalize({ ...fields.rules, ...patch }),
});
