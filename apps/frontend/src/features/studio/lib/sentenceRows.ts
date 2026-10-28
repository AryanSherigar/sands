import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COMPARISONS_BY_KIND } from "../constants/comparisons";
import type {
  Comparison,
  Sentence,
  SentenceJoiner,
  SentenceMetadata,
  ValueOption,
} from "../types/sentence.types";
import {
  buildSentenceMetadata,
  compileSentence,
  compileWhileLimit,
  parseExpression,
  parseWhileLimit,
} from "./sentenceCompiler";

export type SentenceBuilderMode = "condition" | "while-limit";

export interface DraftRow {
  id: string;
  path: string;
  comparison?: Comparison;
  amount?: number | string;
  ref?: string;
}

export type DraftRowInput = Omit<DraftRow, "id">;

export interface DraftSentence {
  rows: DraftRow[];
  joiner: SentenceJoiner;
}

export interface SentenceOutput {
  expression: FieldExpression;
  metadata: SentenceMetadata;
}

const WHILE_LIMIT_ROW_COUNT = 2;

let rowCounter = 0;

export const nextRowId = (): string => {
  rowCounter += 1;
  return `row-${rowCounter}`;
};

const withRowId = (row: DraftRowInput): DraftRow => ({ ...row, id: nextRowId() });

const buildEmptyDraft = (mode: SentenceBuilderMode): DraftSentence => ({
  rows: Array.from({ length: mode === "while-limit" ? WHILE_LIMIT_ROW_COUNT : 1 }, () => withRowId({ path: "" })),
  joiner: "and",
});

const parseValue = (
  value: FieldExpression,
  metadata: SentenceMetadata | undefined,
  mode: SentenceBuilderMode,
): DraftSentence | null => {
  if (mode === "condition") {
    const sentence = parseExpression(value, metadata);
    return sentence ? { rows: sentence.rows.map(withRowId), joiner: sentence.joiner } : null;
  }
  const limit = parseWhileLimit(value, metadata);
  return limit ? { rows: [limit.guard, limit.must].map(withRowId), joiner: "and" } : null;
};

const hasUnsupportedPath = (draft: DraftSentence, isUnsupportedPath: (path: string) => boolean): boolean =>
  draft.rows.some((row) => isUnsupportedPath(row.path) || isUnsupportedPath(row.ref ?? ""));

export const readDraft = (
  value: FieldExpression | null,
  metadata: SentenceMetadata | undefined,
  mode: SentenceBuilderMode,
  isUnsupportedPath: (path: string) => boolean = () => false,
): { draft: DraftSentence; isUnrepresentable: boolean } => {
  if (value === null) return { draft: buildEmptyDraft(mode), isUnrepresentable: false };
  const parsed = parseValue(value, metadata, mode);
  if (parsed === null || hasUnsupportedPath(parsed, isUnsupportedPath)) {
    return { draft: buildEmptyDraft(mode), isUnrepresentable: true };
  }
  return { draft: parsed, isUnrepresentable: false };
};

export const startRowForValue = (option: ValueOption): DraftRowInput => ({
  path: option.path,
  ...(option.kind === "enum" ? { comparison: "becomes_option" as const } : {}),
});

const isAmountComplete = (row: DraftRowInput): boolean => {
  if (row.ref !== undefined) return row.ref !== "";
  if (row.comparison === "becomes_yes" || row.comparison === "becomes_no") return true;
  if (row.comparison === "becomes_option") return typeof row.amount === "string" && row.amount !== "";
  return typeof row.amount === "number" && Number.isFinite(row.amount);
};

const isRowComplete = (row: DraftRowInput, option: ValueOption | undefined): boolean => {
  if (!option || !row.comparison) return false;
  if (!COMPARISONS_BY_KIND[option.kind].includes(row.comparison)) return false;
  return isAmountComplete(row);
};

export const isDraftEmpty = (draft: DraftSentence): boolean => draft.rows.every((row) => !row.path);

export const toSentence = (
  draft: DraftSentence,
  options: readonly ValueOption[],
  mode: SentenceBuilderMode,
): Sentence | null => {
  const isRowCountValid = mode === "condition" || draft.rows.length === WHILE_LIMIT_ROW_COUNT;
  const isEveryRowComplete = draft.rows.every((row) =>
    isRowComplete(row, options.find((option) => option.path === row.path)),
  );
  if (!isRowCountValid || !isEveryRowComplete) return null;
  return { rows: draft.rows.map(({ id: _id, ...row }) => row as Sentence["rows"][number]), joiner: draft.joiner };
};

export const toOutput = (sentence: Sentence, mode: SentenceBuilderMode): SentenceOutput => {
  const metadata = buildSentenceMetadata(sentence);
  if (mode === "condition") return { expression: compileSentence(sentence), metadata };
  const [guard, must] = sentence.rows;
  return { expression: compileWhileLimit(guard, must), metadata };
};

export const findMissingPaths = (
  draft: DraftSentence,
  options: readonly ValueOption[],
): string[] =>
  draft.rows
    .flatMap((row) => [row.path, row.ref ?? ""])
    .filter((path) => path !== "" && !options.some((option) => option.path === path));
