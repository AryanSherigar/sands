import type { ExpressionOperator } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import type { Comparison, ValueKind } from "../types/sentence.types";

export const COMPARISON_OPERATORS: Record<Comparison, ExpressionOperator> = {
  drops_to: "<=",
  rises_to: ">=",
  at_least: ">=",
  at_most: "<=",
  exactly: "==",
  becomes_yes: "==",
  becomes_no: "==",
  becomes_option: "==",
};

export const COMPARISON_LABELS: Record<Comparison, string> = {
  drops_to: "drops to",
  rises_to: "rises to",
  at_least: "is at least",
  at_most: "is at most",
  exactly: "is exactly",
  becomes_yes: "becomes yes",
  becomes_no: "becomes no",
  becomes_option: "becomes",
};

export const COMPARISON_DESCRIPTIONS: Record<Comparison, string> = {
  drops_to: "drops to",
  rises_to: "rises to",
  at_least: "is at least",
  at_most: "is at most",
  exactly: "is exactly",
  becomes_yes: "is yes",
  becomes_no: "is no",
  becomes_option: "is",
};

export const COMPARISONS_BY_KIND: Record<ValueKind, readonly Comparison[]> = {
  number: ["drops_to", "rises_to", "at_least", "at_most", "exactly"],
  boolean: ["becomes_yes", "becomes_no"],
  enum: ["becomes_option"],
};

export const MUST_COMPARISON_LABELS: Record<Comparison, string> = {
  drops_to: "must be at most",
  rises_to: "must be at least",
  at_least: "must be at least",
  at_most: "must be at most",
  exactly: "must be exactly",
  becomes_yes: "must be yes",
  becomes_no: "must be no",
  becomes_option: "must be",
};

export const MUST_COMPARISONS_BY_KIND: Record<ValueKind, readonly Comparison[]> = {
  number: ["at_least", "at_most", "exactly"],
  boolean: ["becomes_yes", "becomes_no"],
  enum: ["becomes_option"],
};
