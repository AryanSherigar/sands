export type ValueKind = "number" | "boolean" | "enum";

type ValueSource = "tracked" | "card";

export interface ValueOption {
  path: string;
  label: string;
  kind: ValueKind;
  options?: string[];
  min?: number;
  max?: number;
  source: ValueSource;
}

export type Comparison =
  | "drops_to"
  | "rises_to"
  | "at_least"
  | "at_most"
  | "exactly"
  | "becomes_yes"
  | "becomes_no"
  | "becomes_option";

export type SentenceJoiner = "and" | "or";

export interface SentenceRow {
  path: string;
  comparison: Comparison;
  amount?: number | string;
  ref?: string;
}

export interface Sentence {
  rows: SentenceRow[];
  joiner: SentenceJoiner;
}

export interface SentenceMetadata {
  rows: Array<{ comparison: Comparison }>;
  joiner: SentenceJoiner;
}

export interface WhileLimit {
  guard: SentenceRow;
  must: SentenceRow;
}
