import React from "react";
import { IconX } from "@tabler/icons-react";
import { Select } from "@/shared/components/ui/Select";
import {
  COMPARISON_LABELS,
  COMPARISONS_BY_KIND,
  MUST_COMPARISON_LABELS,
  MUST_COMPARISONS_BY_KIND,
} from "../../constants/comparisons";
import {
  COMPARE_TO_LABEL,
  COMPARE_TO_OPTIONS,
  COMPARISON_PLACEHOLDER,
  NO_SELECTION,
} from "../../constants/sentenceBuilder";
import { startRowForValue } from "../../lib/sentenceRows";
import type { Comparison } from "../../types/sentence.types";
import { AmountField } from "./AmountField";
import type { SentenceRowProps } from "./SentenceBuilder.types";
import { ValuePicker } from "./ValuePicker";

export const SentenceRow: React.FC<SentenceRowProps> = ({
  row,
  options,
  allOptions,
  rowLabel,
  leadLabel,
  missingName,
  isMustRow = false,
  canCompareToValue = false,
  onChange,
  onRemove,
  onRequestNew,
}) => {
  const selected = allOptions.find((option) => option.path === row.path);
  const numberOptions = allOptions.filter((option) => option.kind === "number");

  const handleSelectValue = (path: string): void => {
    const next = allOptions.find((option) => option.path === path);
    onChange(next ? startRowForValue(next) : { path: "" });
  };
  const handleSelectComparison = (comparison: string): void =>
    onChange({ ...row, comparison: (comparison || undefined) as Comparison | undefined });
  const handleCompareToChange = (target: string): void => {
    const base = { path: row.path, comparison: row.comparison };
    onChange(target === "value" ? { ...base, ref: "" } : base);
  };
  const comparisons = isMustRow ? MUST_COMPARISONS_BY_KIND : COMPARISONS_BY_KIND;
  const comparisonLabels = isMustRow ? MUST_COMPARISON_LABELS : COMPARISON_LABELS;
  const canPickComparisonTarget = canCompareToValue && selected?.kind === "number" && row.comparison !== undefined;

  return (
    <div role="group" aria-label={rowLabel} className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        {leadLabel && <span className="text-meta text-content-muted">{leadLabel}</span>}
        <ValuePicker
          path={row.path}
          options={options}
          missingName={missingName}
          label="Value"
          onSelect={handleSelectValue}
          onRequestNew={onRequestNew}
        />
        {selected && (
          <Select
            aria-label="Comparison"
            className="w-auto min-w-36"
            value={row.comparison ?? NO_SELECTION}
            options={[
              { value: NO_SELECTION, label: COMPARISON_PLACEHOLDER },
              ...comparisons[selected.kind].map((comparison) => ({
                value: comparison,
                label: comparisonLabels[comparison],
              })),
            ]}
            onChange={(event) => handleSelectComparison(event.target.value)}
          />
        )}
        {canPickComparisonTarget && (
          <Select
            aria-label={COMPARE_TO_LABEL}
            className="w-auto min-w-32"
            value={row.ref === undefined ? "amount" : "value"}
            options={COMPARE_TO_OPTIONS}
            onChange={(event) => handleCompareToChange(event.target.value)}
          />
        )}
        {selected && (
          <AmountField row={row} option={selected} numberOptions={numberOptions} onChange={onChange} />
        )}
        {onRemove && (
          <button
            type="button"
            aria-label="Remove row"
            onClick={onRemove}
            className="flex h-8 w-8 items-center justify-center rounded-md text-content-faint transition-colors hover:bg-white/6 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
          >
            <IconX size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      {missingName !== null && (
        <p className="text-meta text-danger">Missing: {missingName}</p>
      )}
    </div>
  );
};
