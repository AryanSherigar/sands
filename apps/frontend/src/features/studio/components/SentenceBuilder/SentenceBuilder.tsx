import React, { useEffect, useMemo, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { GUARD_ROW_LABEL, MAX_SENTENCE_ROWS, MUST_ROW_LABEL } from "../../constants/sentenceBuilder";
import type { FieldExpression } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { useSentenceRows } from "../../hooks/useSentenceRows";
import { useValueOptionsState } from "../../hooks/useValueOptionsState";
import { describeSentence, describeWhileLimit } from "../../lib/sentenceCompiler";
import {
  findMissingPaths,
  startRowForValue,
  toSentence,
  type DraftRow,
  type SentenceBuilderMode,
} from "../../lib/sentenceRows";
import { humanizeKey } from "../../lib/valueOptions";
import type { Sentence, ValueOption } from "../../types/sentence.types";
import { AdvancedLogicNotice } from "./AdvancedLogicNotice";
import { JoinerPicker } from "./JoinerPicker";
import { NewValueInline } from "./NewValueInline";
import { SentencePreview } from "./SentencePreview";
import { SentenceRow } from "./SentenceRow";
import type { SentenceBuilderProps } from "./SentenceBuilder.types";

const isEmptyExpression = (expression: FieldExpression | null): boolean =>
  expression !== null && Object.keys(expression).length === 0;

const nameFromPath = (path: string): string => humanizeKey(path.split(".").at(-1) ?? path);

const buildPreview = (sentence: Sentence, mode: SentenceBuilderMode, labels: Record<string, string>): string => {
  if (mode === "condition") return describeSentence(sentence, labels);
  const [guard, must] = sentence.rows;
  return describeWhileLimit({ guard, must }, labels);
};

const readMissingName = (row: DraftRow, missingPaths: string[]): string | null => {
  const missing = [row.path, row.ref ?? ""].find((path) => path !== "" && missingPaths.includes(path));
  return missing === undefined ? null : nameFromPath(missing);
};

const readLeadLabel = (mode: SentenceBuilderMode, index: number): string | undefined => {
  if (mode !== "while-limit") return undefined;
  return index === 0 ? GUARD_ROW_LABEL : MUST_ROW_LABEL;
};

export const SentenceBuilder: React.FC<SentenceBuilderProps> = ({
  value: rawValue,
  metadata,
  onChange,
  onOpenFullEditor,
  onValidityChange,
  mode = "condition",
  scopeFilter,
  canCompareToValue = false,
  maxRows = MAX_SENTENCE_ROWS,
}) => {
  const { options: allOptions, isUnsupportedPath, isLoading: isLoadingOptions } = useValueOptionsState();
  const value = isEmptyExpression(rawValue) ? null : rawValue;
  const options = useMemo(
    (): ValueOption[] => (scopeFilter ? allOptions.filter(scopeFilter) : allOptions),
    [allOptions, scopeFilter],
  );
  const rows = useSentenceRows({ value, metadata, mode, options: allOptions, isUnsupportedPath, onChange });
  const [creatingRowId, setCreatingRowId] = useState<string | null>(null);
  const missingPaths = isLoadingOptions ? [] : findMissingPaths(rows.draft, allOptions);
  const isValid = missingPaths.length === 0;

  useEffect(() => {
    if (!isLoadingOptions) onValidityChange?.(isValid);
  }, [isLoadingOptions, isValid, onValidityChange]);

  if (rows.isUnrepresentable) return <AdvancedLogicNotice onOpenFullEditor={onOpenFullEditor} />;

  const sentence = toSentence(rows.draft, allOptions, mode);
  const labels = Object.fromEntries(allOptions.map((option) => [option.path, option.label]));
  const canEditRows = mode === "condition";

  const handleCreated = (index: number, option: ValueOption): void => {
    rows.updateRow(index, startRowForValue(option));
    setCreatingRowId(null);
  };

  return (
    <div className="space-y-3">
      {rows.draft.rows.map((row, index) => (
        <div key={row.id} className="space-y-2">
          <SentenceRow
            row={row}
            options={options}
            allOptions={allOptions}
            rowLabel={`Row ${index + 1}`}
            leadLabel={readLeadLabel(mode, index)}
            isMustRow={mode === "while-limit" && index === 1}
            canCompareToValue={canCompareToValue}
            missingName={readMissingName(row, missingPaths)}
            onChange={(next) => rows.updateRow(index, next)}
            onRemove={canEditRows && rows.draft.rows.length > 1 ? () => rows.removeRow(index) : undefined}
            onRequestNew={() => setCreatingRowId(row.id)}
          />
          {creatingRowId === row.id && (
            <NewValueInline
              onCreated={(option) => handleCreated(index, option)}
              onCancel={() => setCreatingRowId(null)}
            />
          )}
        </div>
      ))}
      {canEditRows && rows.draft.rows.length > 1 && (
        <JoinerPicker joiner={rows.draft.joiner} onChange={rows.setJoiner} />
      )}
      {canEditRows && rows.draft.rows.length < maxRows && (
        <Button type="button" variant="ghost" size="sm" onClick={rows.addRow}>
          + Add another
        </Button>
      )}
      {sentence && <SentencePreview text={buildPreview(sentence, mode, labels)} />}
    </div>
  );
};
