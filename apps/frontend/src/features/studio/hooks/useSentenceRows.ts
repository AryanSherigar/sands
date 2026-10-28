import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { MAX_SENTENCE_ROWS } from "../constants/sentenceBuilder";
import {
  isDraftEmpty,
  readDraft,
  toOutput,
  toSentence,
  nextRowId,
  type DraftRowInput,
  type DraftSentence,
  type SentenceBuilderMode,
  type SentenceOutput,
} from "../lib/sentenceRows";
import type { SentenceJoiner, SentenceMetadata, ValueOption } from "../types/sentence.types";

interface UseSentenceRowsParams {
  value: FieldExpression | null;
  metadata?: SentenceMetadata;
  mode: SentenceBuilderMode;
  options: readonly ValueOption[];
  isUnsupportedPath: (path: string) => boolean;
  onChange: (next: SentenceOutput | null) => void;
}

export interface SentenceRows {
  draft: DraftSentence;
  isUnrepresentable: boolean;
  updateRow: (index: number, row: DraftRowInput) => void;
  addRow: () => void;
  removeRow: (index: number) => void;
  setJoiner: (joiner: SentenceJoiner) => void;
}

const fingerprint = (value: FieldExpression | null): string | null =>
  value === null ? null : JSON.stringify(value);

export const useSentenceRows = ({
  value,
  metadata,
  mode,
  options,
  isUnsupportedPath,
  onChange,
}: UseSentenceRowsParams): SentenceRows => {
  const parsed = useMemo(
    () => readDraft(value, metadata, mode, isUnsupportedPath),
    [isUnsupportedPath, metadata, mode, value],
  );
  const [draft, setDraft] = useState<DraftSentence>(parsed.draft);
  const lastEmitted = useRef<string | null>(fingerprint(value));

  useEffect(() => {
    const incoming = fingerprint(value);
    if (incoming === lastEmitted.current) return;
    lastEmitted.current = incoming;
    setDraft(parsed.draft);
  }, [parsed, value]);

  const commit = useCallback(
    (next: DraftSentence): void => {
      if (parsed.isUnrepresentable) return;
      setDraft(next);
      const sentence = toSentence(next, options, mode);
      if (sentence) {
        const output = toOutput(sentence, mode);
        lastEmitted.current = fingerprint(output.expression);
        onChange(output);
      } else if (isDraftEmpty(next)) {
        lastEmitted.current = null;
        onChange(null);
      }
    },
    [mode, onChange, options, parsed.isUnrepresentable],
  );

  const updateRow = useCallback(
    (index: number, row: DraftRowInput): void =>
      commit({
        ...draft,
        rows: draft.rows.map((current, at) => (at === index ? { ...row, id: current.id } : current)),
      }),
    [commit, draft],
  );
  const addRow = useCallback((): void => {
    if (draft.rows.length >= MAX_SENTENCE_ROWS) return;
    commit({ ...draft, rows: [...draft.rows, { id: nextRowId(), path: "" }] });
  }, [commit, draft]);
  const removeRow = useCallback(
    (index: number): void => commit({ ...draft, rows: draft.rows.filter((_, at) => at !== index) }),
    [commit, draft],
  );
  const setJoiner = useCallback((joiner: SentenceJoiner): void => commit({ ...draft, joiner }), [commit, draft]);

  return {
    draft,
    isUnrepresentable: parsed.isUnrepresentable,
    updateRow,
    addRow,
    removeRow,
    setJoiner,
  };
};
