import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { StateMutationOp } from "@/shared/types/stateMutation.types";
import { MUTATION_OP_OPTIONS } from "../../constants/stateMutation";
import { StateMutationRowProps } from "./StateMutationRow.types";

export const StateMutationRow: React.FC<StateMutationRowProps> = ({
  index,
  total,
  mutation,
  onChange,
  onMove,
  onRemove,
}) => {
  const position = index + 1;

  const handlePathChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => onChange(index, { ...mutation, path: event.target.value });

  const handleOpChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    onChange(index, { ...mutation, op: event.target.value as StateMutationOp });

  const handleValueChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => onChange(index, { ...mutation, value: event.target.value });

  const handleMoveUp = (): void => onMove(index, -1);
  const handleMoveDown = (): void => onMove(index, 1);
  const handleRemove = (): void => onRemove(index);

  return (
    <li className="flex items-center gap-2">
      <Input
        value={mutation.path}
        onChange={handlePathChange}
        placeholder="path, e.g. player.sanity"
        aria-label={`Mutation ${position} path`}
      />
      <div className="w-36 shrink-0">
        <Select
          aria-label={`Mutation ${position} operation`}
          options={MUTATION_OP_OPTIONS}
          value={mutation.op}
          onChange={handleOpChange}
        />
      </div>
      <Input
        value={String(mutation.value)}
        onChange={handleValueChange}
        placeholder="value"
        aria-label={`Mutation ${position} value`}
      />
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={index === 0}
        onClick={handleMoveUp}
        aria-label={`Move mutation ${position} up`}
      >
        ↑
      </Button>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={index === total - 1}
        onClick={handleMoveDown}
        aria-label={`Move mutation ${position} down`}
      >
        ↓
      </Button>
      <Button
        type="button"
        variant="danger"
        size="sm"
        onClick={handleRemove}
        aria-label={`Remove mutation ${position}`}
      >
        Remove
      </Button>
    </li>
  );
};
