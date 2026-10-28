import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COPY_SUFFIX } from "../constants/advancedCards";
import {
  APPLIES_TO_EVERYONE,
  APPLIES_TO_PLAYER,
  LIMIT_LABEL_MAX_LENGTH,
  NEW_LIMIT_LABEL,
  type LimitKind,
} from "../constants/hardLimits";
import type { EntityResponse } from "../types/entity.types";
import type { InvariantCreate, InvariantResponse, InvariantUpdate } from "../types/invariant.types";
import type { Sentence, SentenceMetadata, ValueOption } from "../types/sentence.types";
import { readExpression } from "./endingDraft";
import {
  describeSentence,
  describeWhileLimit,
  parseExpression,
  parseWhileLimit,
} from "./sentenceCompiler";
import { readSentenceMetadata, toStoredMetadata } from "./sentenceMetadata";
import { extractFieldPaths } from "./valueOptions";

export interface LimitDraft {
  expression: FieldExpression | null;
  metadata: SentenceMetadata | undefined;
  appliesTo: string;
  text: string;
}

export const inferLimitKind = (expression: FieldExpression | null): LimitKind =>
  expression && parseWhileLimit(expression) ? "while" : "compare";


const describeLimit = (
  draft: Pick<LimitDraft, "expression" | "metadata">,
  labels: Record<string, string>,
): string | null => {
  if (!draft.expression) return null;
  const limit = parseWhileLimit(draft.expression, draft.metadata);
  if (limit) return describeWhileLimit(limit, labels);
  const sentence = parseExpression(draft.expression, draft.metadata);
  return sentence ? `Always: ${describeSentence(sentence, labels)}` : null;
};

export const buildSuggestedText = (draft: LimitDraft, labels: Record<string, string>): string => {
  const description = describeLimit(draft, labels);
  return description ? `${description}.` : "";
};

export const buildLimitDraft = (row: InvariantResponse, labels: Record<string, string>): LimitDraft => {
  const stored: LimitDraft = {
    expression: readExpression(row.invariant_expression),
    metadata: readSentenceMetadata(row.metadata),
    appliesTo: row.applies_to,
    text: row.narrator_text,
  };
  const isSuggestion = row.narrator_text === buildSuggestedText(stored, labels);
  return isSuggestion ? { ...stored, text: "" } : stored;
};

export const readEffectiveText = (draft: LimitDraft, labels: Record<string, string>): string =>
  draft.text.trim() || buildSuggestedText(draft, labels);

const buildLimitLabel = (draft: LimitDraft, labels: Record<string, string>): string =>
  (describeLimit(draft, labels) ?? NEW_LIMIT_LABEL).slice(0, LIMIT_LABEL_MAX_LENGTH);

const isSameExpression = (row: InvariantResponse, draft: LimitDraft): boolean =>
  JSON.stringify(row.invariant_expression ?? {}) === JSON.stringify(draft.expression ?? {});

export const buildLimitPatch = (
  row: InvariantResponse,
  draft: LimitDraft,
  labels: Record<string, string>,
  isExpressionBlocked = false,
): InvariantUpdate => {
  const patch: InvariantUpdate = {};
  const text = readEffectiveText(draft, labels);
  if (text !== row.narrator_text) patch.narrator_text = text;
  if (draft.appliesTo !== row.applies_to) patch.applies_to = draft.appliesTo;
  if (!isExpressionBlocked && !isSameExpression(row, draft)) {
    patch.invariant_expression = (draft.expression ?? {}) as unknown as Record<string, unknown>;
    patch.metadata = toStoredMetadata(draft.metadata, row.metadata);
    patch.label = buildLimitLabel(draft, labels);
  }
  return patch;
};

export const buildNewLimit = (): InvariantCreate => ({
  label: NEW_LIMIT_LABEL,
  invariant_expression: {},
  applies_to: APPLIES_TO_PLAYER,
  narrator_text: "",
});

export const buildLimitCopy = (row: InvariantResponse): InvariantCreate => ({
  label: `${row.label} (${COPY_SUFFIX})`.slice(0, LIMIT_LABEL_MAX_LENGTH),
  invariant_expression: row.invariant_expression,
  applies_to: row.applies_to,
  narrator_text: row.narrator_text,
  ...(row.metadata ? { metadata: row.metadata } : {}),
});

const isInScope = (option: ValueOption, appliesTo: string, playerId: string | undefined): boolean => {
  if (appliesTo === APPLIES_TO_EVERYONE) return option.source === "tracked";
  if (appliesTo === APPLIES_TO_PLAYER) {
    return option.source === "tracked" || (playerId !== undefined && option.path.startsWith(`${playerId}.`));
  }
  return option.source === "tracked" || option.path.startsWith(`${appliesTo}.`);
};

export const buildScopeFilter = (
  appliesTo: string,
  entities: readonly EntityResponse[],
  expression: FieldExpression | null,
): ((option: ValueOption) => boolean) => {
  const playerId = entities.find((entity) => entity.is_player)?.entity_id;
  const used = expression ? extractFieldPaths(expression as unknown as Record<string, unknown>) : new Set<string>();
  return (option) => used.has(option.path) || isInScope(option, appliesTo, playerId);
};

const readLiteralSentence = (draft: LimitDraft): Sentence | null => {
  if (!draft.expression) return null;
  const sentence = parseExpression(draft.expression, draft.metadata);
  const isSingleLiteral = sentence?.rows.length === 1 && sentence.rows[0].ref === undefined;
  return isSingleLiteral ? sentence : null;
};

export const findRedundantBoundMessage = (
  draft: LimitDraft,
  options: readonly ValueOption[],
): string | null => {
  const row = readLiteralSentence(draft)?.rows[0];
  const option = row ? options.find((candidate) => candidate.path === row.path) : undefined;
  if (!row || !option || typeof row.amount !== "number") return null;
  const isLowest = (row.comparison === "at_least" || row.comparison === "rises_to") && row.amount === option.min;
  const isHighest = (row.comparison === "at_most" || row.comparison === "drops_to") && row.amount === option.max;
  if (isLowest) return `${option.label}'s lowest value already does this.`;
  return isHighest ? `${option.label}'s highest value already does this.` : null;
};

const hasCardValues = (entity: EntityResponse): boolean =>
  Object.values(entity.attributes_schema ?? {}).some((field) =>
    ["number", "boolean", "enum"].includes(field.type),
  );

export const listAppliesToCards = (entities: readonly EntityResponse[], current: string): EntityResponse[] =>
  entities.filter((entity) => entity.entity_id === current || (!entity.is_player && hasCardValues(entity)));
