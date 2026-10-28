import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import {
  HIDDEN_TAB_GRACE_SECONDS,
  MAX_CHECK_OPTIONS,
  MAX_REOPENS,
} from "../../constants/ruleCheck";
import { OptionRow } from "./OptionRow";
import { ResultSelect } from "./ResultSelect";
import { buildEmptyOption } from "./ruleCheckFormState";
import { TimedChoiceFieldsProps } from "./TimedChoiceFields.types";
import { WindowSlider } from "./WindowSlider";
import type { CheckOptionShape } from "../../types/ruleCheck.types";

const HIDDEN_RESULT_HELP = `Used if the player leaves the tab for more than ${HIDDEN_TAB_GRACE_SECONDS} s. Leave blank for no penalty.`;

export const TimedChoiceFields: React.FC<TimedChoiceFieldsProps> = ({
  value,
  resultChoices,
  onChange,
}) => {
  const canAddOption = value.options.length < MAX_CHECK_OPTIONS;

  const handleOptionChange = (index: number, option: CheckOptionShape): void =>
    onChange({
      ...value,
      options: value.options.map((item, itemIndex) =>
        itemIndex === index ? option : item,
      ),
    });

  const handleOptionRemove = (index: number): void =>
    onChange({
      ...value,
      options: value.options.filter((_, itemIndex) => itemIndex !== index),
    });

  const handleAddOption = (): void =>
    onChange({
      ...value,
      options: [...value.options, buildEmptyOption(value.options.length)],
    });

  const handlePromptChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ): void => onChange({ ...value, prompt: event.target.value });

  const handleReopensChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => onChange({ ...value, maxReopens: Number(event.target.value) });

  return (
    <div className="space-y-3">
      <textarea
        aria-label="Prompt"
        value={value.prompt}
        onChange={handlePromptChange}
        placeholder="What the player reads, e.g. The lamp in Cabin 14 has gone out."
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={2}
      />
      <ul className="space-y-2">
        {value.options.map((option, index) => (
          <OptionRow
            key={index}
            index={index}
            option={option}
            resultChoices={resultChoices}
            canRemove={value.options.length > 2}
            onChange={handleOptionChange}
            onRemove={handleOptionRemove}
          />
        ))}
      </ul>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={!canAddOption}
        onClick={handleAddOption}
      >
        Add option
      </Button>
      <WindowSlider
        seconds={value.windowSeconds}
        onChange={(windowSeconds) => onChange({ ...value, windowSeconds })}
      />
      <ResultSelect
        label="Result when time runs out"
        value={value.timeoutResult}
        choices={resultChoices}
        onChange={(timeoutResult) => onChange({ ...value, timeoutResult })}
      />
      <ResultSelect
        label="Result when the tab is hidden"
        value={value.hiddenResult}
        choices={resultChoices}
        isOptional
        helpText={HIDDEN_RESULT_HELP}
        onChange={(hiddenResult) => onChange({ ...value, hiddenResult })}
      />
      <label className="block text-sm text-content-muted">
        Times an option may re-open
        <Input
          type="number"
          aria-label="Times an option may re-open"
          min={0}
          max={MAX_REOPENS}
          value={value.maxReopens}
          onChange={handleReopensChange}
        />
      </label>
    </div>
  );
};
