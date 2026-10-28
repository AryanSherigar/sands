import { COMPARISON_OPERATORS } from "../constants/comparisons";
import type { Comparison, SentenceJoiner, SentenceMetadata } from "../types/sentence.types";

const SENTENCE_KEYS = ["rows", "joiner"];

type StoredMetadata = Record<string, unknown> | null | undefined;

const isComparison = (value: unknown): value is Comparison =>
  typeof value === "string" && value in COMPARISON_OPERATORS;

const isJoiner = (value: unknown): value is SentenceJoiner => value === "and" || value === "or";

const readRow = (raw: unknown): { comparison: Comparison } | null => {
  if (typeof raw !== "object" || raw === null) return null;
  const comparison = (raw as { comparison?: unknown }).comparison;
  return isComparison(comparison) ? { comparison } : null;
};

export const readSentenceMetadata = (stored: StoredMetadata): SentenceMetadata | undefined => {
  if (!stored || !Array.isArray(stored.rows) || !isJoiner(stored.joiner)) return undefined;
  const rows = stored.rows.map(readRow);
  if (rows.some((row) => row === null)) return undefined;
  return { rows: rows as SentenceMetadata["rows"], joiner: stored.joiner };
};

export const toStoredMetadata = (
  metadata: SentenceMetadata | undefined,
  existing: StoredMetadata = null,
): Record<string, unknown> | null => {
  const unrelated = Object.fromEntries(
    Object.entries(existing ?? {}).filter(([key]) => !SENTENCE_KEYS.includes(key)),
  );
  if (metadata) return { ...unrelated, rows: metadata.rows, joiner: metadata.joiner };
  return Object.keys(unrelated).length > 0 ? unrelated : null;
};
