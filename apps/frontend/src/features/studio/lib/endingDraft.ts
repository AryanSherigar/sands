import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COPY_SUFFIX } from "../constants/advancedCards";
import type {
  EndConditionCreate,
  EndConditionResponse,
  EndConditionUpdate,
  OutcomeTag,
} from "../types/end_condition.types";
import type { SentenceMetadata } from "../types/sentence.types";
import { readSentenceMetadata, toStoredMetadata } from "./sentenceMetadata";

export interface EndingDraft {
  title: string;
  tag: OutcomeTag;
  isSecret: boolean;
  expression: FieldExpression | null;
  metadata: SentenceMetadata | undefined;
  text: string;
}

export const readExpression = (stored: Record<string, unknown> | null | undefined): FieldExpression | null =>
  stored && Object.keys(stored).length > 0 ? (stored as unknown as FieldExpression) : null;

export const buildEndingDraft = (row: EndConditionResponse): EndingDraft => ({
  title: row.outcome_title,
  tag: row.outcome_tag,
  isSecret: row.is_secret,
  expression: readExpression(row.condition_expression),
  metadata: readSentenceMetadata(row.metadata),
  text: row.outcome_text,
});

const isSameExpression = (row: EndConditionResponse, draft: EndingDraft): boolean =>
  JSON.stringify(row.condition_expression ?? {}) === JSON.stringify(draft.expression ?? {});

export const buildEndingPatch = (
  row: EndConditionResponse,
  draft: EndingDraft,
  isExpressionBlocked = false,
): EndConditionUpdate => {
  const patch: EndConditionUpdate = {};
  if (draft.title !== row.outcome_title) patch.outcome_title = draft.title;
  if (draft.tag !== row.outcome_tag) patch.outcome_tag = draft.tag;
  if (draft.isSecret !== row.is_secret) patch.is_secret = draft.isSecret;
  if (draft.text !== row.outcome_text) patch.outcome_text = draft.text;
  if (!isExpressionBlocked && !isSameExpression(row, draft)) {
    patch.condition_expression = (draft.expression ?? {}) as unknown as Record<string, unknown>;
    patch.metadata = toStoredMetadata(draft.metadata, row.metadata);
  }
  return patch;
};

export const buildNewEnding = (tag: OutcomeTag, priority: number): EndConditionCreate => ({
  outcome_tag: tag,
  outcome_title: "",
  outcome_text: "",
  condition_expression: {},
  is_secret: false,
  priority,
});

export const buildEndingCopy = (row: EndConditionResponse, priority: number): EndConditionCreate => ({
  outcome_tag: row.outcome_tag,
  outcome_title: row.outcome_title.trim() ? `${row.outcome_title} (${COPY_SUFFIX})` : "",
  outcome_text: row.outcome_text,
  condition_expression: row.condition_expression,
  is_secret: row.is_secret,
  priority,
  ...(row.metadata ? { metadata: row.metadata } : {}),
});
