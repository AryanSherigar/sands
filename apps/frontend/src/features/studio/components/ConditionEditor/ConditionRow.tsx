import React from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { ConditionRowProps } from "./ConditionRow.types";

export const ConditionRow: React.FC<ConditionRowProps> = ({
  condition,
  onEdit,
  onDelete,
}) => {
  const mutationCount = condition.state_mutations?.length ?? 0;
  const handleEditClick = (): void => onEdit(condition);
  const handleDeleteClick = (): void => onDelete(condition.condition_id);

  return (
    <div className="rounded-md flex items-center justify-between border border-border-subtle bg-surface px-3 py-2">
      <button
        type="button"
        onClick={handleEditClick}
        className="flex flex-1 flex-col items-start gap-1 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm text-content">{condition.label}</span>
          {mutationCount > 0 && (
            <Badge variant="warning">
              {mutationCount === 1 ? "1 mutation" : `${mutationCount} mutations`}
            </Badge>
          )}
          {condition.is_one_shot && <Badge variant="info">Once</Badge>}
          {condition.sensory_cue && (
            <Badge variant="default">Cue: {condition.sensory_cue}</Badge>
          )}
        </div>
        <span className="text-xs text-content-faint">
          {condition.narrator_instruction}
        </span>
      </button>
      <Button
        type="button"
        variant="danger"
        size="sm"
        onClick={handleDeleteClick}
      >
        Delete
      </Button>
    </div>
  );
};
