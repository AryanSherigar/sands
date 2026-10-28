import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { StateMutationOp } from "@/shared/types/stateMutation.types";
import {
  MUTATION_OP_OPTIONS,
  buildEmptyMutation,
} from "../../constants/stateMutation";
import { StateMutationFieldsProps } from "./StateMutationFields.types";

const EMPTY_MUTATION = buildEmptyMutation();

export const StateMutationFields: React.FC<StateMutationFieldsProps> = ({
  value,
  onChange,
  isOptional = true,
}) => {
  const hasStateMutation = value !== null;
  const displayValue = value ?? EMPTY_MUTATION;
  const showFields = isOptional ? hasStateMutation : true;

  const handleToggle = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange(event.target.checked ? EMPTY_MUTATION : null);
  };

  const handlePathChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    onChange({ ...displayValue, path: event.target.value });
  };

  const handleOpChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
  ): void => {
    onChange({ ...displayValue, op: event.target.value as StateMutationOp });
  };

  const handleValueChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    onChange({ ...displayValue, value: event.target.value });
  };

  return (
    <div className="rounded-md space-y-2 border border-border-subtle p-3">
      {isOptional && (
        <label className="flex items-center gap-2 text-sm text-content-muted">
          <input
            type="checkbox"
            checked={hasStateMutation}
            onChange={handleToggle}
          />
          Has state mutation (Effect C)
        </label>
      )}
      {showFields && (
        <div className="flex items-center gap-2">
          <Input
            value={displayValue.path}
            onChange={handlePathChange}
            placeholder="path, e.g. player.sanity"
            aria-label="Mutation path"
          />
          <div className="w-36 shrink-0">
            <Select
              aria-label="Mutation operation"
              options={MUTATION_OP_OPTIONS}
              value={displayValue.op}
              onChange={handleOpChange}
            />
          </div>
          <Input
            value={String(displayValue.value)}
            onChange={handleValueChange}
            placeholder="value"
            aria-label="Mutation value"
          />
        </div>
      )}
    </div>
  );
};
