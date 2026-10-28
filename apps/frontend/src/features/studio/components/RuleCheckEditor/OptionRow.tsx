import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { StateMutation } from "@/shared/types/stateMutation.types";
import { MAX_OPTION_MUTATIONS } from "../../constants/ruleCheck";
import { StateMutationList } from "../ConditionEditor/StateMutationList";
import { OptionRowProps } from "./OptionRow.types";

const NO_RESULT_OPTION = { value: "", label: "Choose a result" };

export const OptionRow: React.FC<OptionRowProps> = ({
  index,
  option,
  resultChoices,
  canRemove,
  onChange,
  onRemove,
}) => {
  const position = index + 1;
  const resultOptions = [
    NO_RESULT_OPTION,
    ...resultChoices.map((choice) => ({ value: choice, label: choice || "(empty)" })),
  ];

  const handleIdChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    onChange(index, { ...option, id: event.target.value });

  const handleLabelChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => onChange(index, { ...option, label: event.target.value });

  const handleResultChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
  ): void => onChange(index, { ...option, result: event.target.value });

  const handleReopensChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => onChange(index, { ...option, reopens: event.target.checked });

  const handleMutationsChange = (mutations: StateMutation[]): void =>
    onChange(index, { ...option, mutations });

  const handleRemove = (): void => onRemove(index);

  return (
    <li className="rounded-md space-y-2 border border-border-subtle p-3">
      <div className="grid grid-cols-3 gap-2">
        <Input
          aria-label={`Option ${position} label`}
          value={option.label}
          onChange={handleLabelChange}
          placeholder="What the player reads"
        />
        <Input
          aria-label={`Option ${position} id`}
          value={option.id}
          onChange={handleIdChange}
          placeholder="id"
        />
        <Select
          aria-label={`Option ${position} result`}
          options={resultOptions}
          value={option.result}
          onChange={handleResultChange}
        />
      </div>
      <StateMutationList
        legend={`Option ${position} also changes`}
        value={option.mutations}
        onChange={handleMutationsChange}
        maxItems={MAX_OPTION_MUTATIONS}
      />
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-xs text-content-muted">
          <input
            type="checkbox"
            checked={option.reopens}
            onChange={handleReopensChange}
          />
          {`Option ${position} re-opens after a narrated exchange`}
        </label>
        <Button
          type="button"
          variant="danger"
          size="sm"
          disabled={!canRemove}
          onClick={handleRemove}
          aria-label={`Remove option ${position}`}
        >
          Remove
        </Button>
      </div>
    </li>
  );
};
