import React from "react";
import { IconX } from "@tabler/icons-react";
import { Select } from "@/shared/components/ui/Select";
import type { StateMutationOp } from "@/shared/types/stateMutation.types";
import { CHANGE_OP_LABELS } from "../../../constants/rules";
import { ADVANCED_LOGIC_MESSAGE, NO_SELECTION, VALUE_PLACEHOLDER } from "../../../constants/sentenceBuilder";
import { useValueOptionsState } from "../../../hooks/useValueOptionsState";
import { buildEmptyChangeRow, listOpsForKind } from "../../../lib/changeRows";
import { humanizeKey } from "../../../lib/valueOptions";
import type { ChangeRowFieldsProps } from "./Advanced.types";
import { ChangeAmountInput } from "./ChangeAmountInput";

export const ChangeRowFields: React.FC<ChangeRowFieldsProps> = ({ row, rowLabel, options, onChange, onRemove }) => {
  const option = options.find((candidate) => candidate.path === row.path);
  const { isUnsupportedPath } = useValueOptionsState();
  const hasNoOption = row.path !== "" && !option;
  const pathName = humanizeKey(row.path.split(".").at(-1) ?? row.path);
  const isUnsupported = hasNoOption && isUnsupportedPath(row.path);
  const missingName = hasNoOption && !isUnsupported ? pathName : null;
  const leading = hasNoOption ? [{ value: row.path, label: pathName }] : [];

  return (
    <div role="group" aria-label={rowLabel} className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <Select
          aria-label="Value to change"
          className="w-auto min-w-40"
          value={row.path}
          options={[
            { value: NO_SELECTION, label: VALUE_PLACEHOLDER },
            ...leading,
            ...options.map((candidate) => ({ value: candidate.path, label: candidate.label })),
          ]}
          onChange={(event) => onChange({ ...buildEmptyChangeRow(row.id), path: event.target.value })}
        />
        {option && (
          <Select
            aria-label="How it changes"
            className="w-auto min-w-32"
            value={row.op}
            options={listOpsForKind(option.kind).map((op: StateMutationOp) => ({ value: op, label: CHANGE_OP_LABELS[op] }))}
            onChange={(event) => onChange({ ...row, op: event.target.value as StateMutationOp })}
          />
        )}
        {option && <ChangeAmountInput row={row} option={option} onChange={(value) => onChange({ ...row, value })} />}
        <button
          type="button"
          aria-label={`Remove ${rowLabel.toLowerCase()}`}
          onClick={onRemove}
          className="flex h-8 w-8 items-center justify-center rounded-md text-content-faint hover:bg-surface-overlay hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
        >
          <IconX size={14} aria-hidden="true" />
        </button>
      </div>
      {missingName !== null && <p className="text-meta text-danger">Missing: {missingName}</p>}
      {isUnsupported && <p className="text-meta text-content-muted">{ADVANCED_LOGIC_MESSAGE}</p>}
    </div>
  );
};
