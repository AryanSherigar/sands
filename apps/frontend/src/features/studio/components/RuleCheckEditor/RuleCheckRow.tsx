import React from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import {
  NOT_EDITABLE_KINDS,
  NOT_EDITABLE_NOTE,
  RULE_CHECK_KIND_OPTIONS,
  TIME_ENTRY_KIND_LABEL,
} from "../../constants/ruleCheck";
import { RuleCheckRowProps } from "./RuleCheckRow.types";

const kindLabel = (kind: string): string => {
  if (kind === "time_entry") return TIME_ENTRY_KIND_LABEL;
  return (
    RULE_CHECK_KIND_OPTIONS.find((option) => option.value === kind)?.label ??
    kind
  );
};

const isEditableKind = (kind: string): boolean =>
  !NOT_EDITABLE_KINDS.some((notEditable) => notEditable === kind);

export const RuleCheckRow: React.FC<RuleCheckRowProps> = ({
  check,
  index,
  total,
  onEdit,
  onDelete,
  onMove,
}) => {
  const isEditable = isEditableKind(check.kind);
  const handleEdit = (): void => onEdit(check);
  const handleDelete = (): void => onDelete(check.check_id);
  const handleMoveUp = (): void => onMove(index, -1);
  const handleMoveDown = (): void => onMove(index, 1);

  return (
    <li
      data-testid={`rule-check-row-${check.check_id}`}
      className="rounded-md flex items-center gap-3 border border-border-subtle bg-surface-inset px-3 py-2"
    >
      <Badge>{kindLabel(check.kind)}</Badge>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-content">{check.label}</p>
        <p className="truncate text-xs text-content-faint">
          stores its answer in {check.result_path}
        </p>
        {!isEditable && (
          <p className="truncate text-xs text-content-faint">
            {NOT_EDITABLE_NOTE}
          </p>
        )}
      </div>
      <Button
        variant="secondary"
        size="sm"
        disabled={index === 0}
        onClick={handleMoveUp}
        aria-label={`Move ${check.label} up`}
      >
        ↑
      </Button>
      <Button
        variant="secondary"
        size="sm"
        disabled={index === total - 1}
        onClick={handleMoveDown}
        aria-label={`Move ${check.label} down`}
      >
        ↓
      </Button>
      {isEditable && (
        <Button variant="secondary" size="sm" onClick={handleEdit}>
          Edit
        </Button>
      )}
      <Button variant="danger" size="sm" onClick={handleDelete}>
        Delete
      </Button>
    </li>
  );
};
