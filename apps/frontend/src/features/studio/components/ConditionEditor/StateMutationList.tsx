import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { moveItem } from "@/shared/lib/moveItem";
import { StateMutation } from "@/shared/types/stateMutation.types";
import {
  MAX_MUTATIONS_PER_LIST,
  buildEmptyMutation,
} from "../../constants/stateMutation";
import { StateMutationRow } from "./StateMutationRow";
import { StateMutationListProps } from "./StateMutationList.types";

export const StateMutationList: React.FC<StateMutationListProps> = ({
  value,
  onChange,
  legend = "State mutations",
  maxItems = MAX_MUTATIONS_PER_LIST,
}) => {
  const isAtLimit = value.length >= maxItems;

  const handleAdd = (): void => onChange([...value, buildEmptyMutation()]);

  const handleRowChange = (index: number, mutation: StateMutation): void =>
    onChange(value.map((item, itemIndex) => (itemIndex === index ? mutation : item)));

  const handleMove = (index: number, offset: number): void =>
    onChange(moveItem(value, index, index + offset));

  const handleRemove = (index: number): void =>
    onChange(value.filter((_, itemIndex) => itemIndex !== index));

  return (
    <fieldset className="rounded-md space-y-2 border border-border-subtle p-3">
      <legend className="px-1 text-sm text-content-muted">{legend}</legend>
      {value.length > 0 && (
        <ol className="space-y-2">
          {value.map((mutation, index) => (
            <StateMutationRow
              key={index}
              index={index}
              total={value.length}
              mutation={mutation}
              onChange={handleRowChange}
              onMove={handleMove}
              onRemove={handleRemove}
            />
          ))}
        </ol>
      )}
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={isAtLimit}
          onClick={handleAdd}
        >
          Add mutation
        </Button>
        {isAtLimit && (
          <span className="text-xs text-content-faint">
            Up to {maxItems} mutations per rule.
          </span>
        )}
      </div>
    </fieldset>
  );
};
