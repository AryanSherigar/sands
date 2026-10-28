import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { MAX_RECALL_VARIANTS } from "../../constants/ruleCheck";
import { ResultSelect } from "./ResultSelect";
import { RecallFieldsProps } from "./RecallFields.types";
import { WindowSlider } from "./WindowSlider";

export const RecallFields: React.FC<RecallFieldsProps> = ({
  value,
  resultChoices,
  onChange,
}) => {
  const canAddVariant = value.variants.length < MAX_RECALL_VARIANTS;

  const handleVariantChange = (index: number, text: string): void =>
    onChange({
      ...value,
      variants: value.variants.map((item, itemIndex) =>
        itemIndex === index ? text : item,
      ),
    });

  const handleVariantRemove = (index: number): void => {
    const variants = value.variants.filter((_, itemIndex) => itemIndex !== index);
    const correctIndex = Math.min(value.correctIndex, variants.length - 1);
    onChange({ ...value, variants, correctIndex });
  };

  const handleAddVariant = (): void =>
    onChange({ ...value, variants: [...value.variants, ""] });

  const handlePromptChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>,
  ): void => onChange({ ...value, prompt: event.target.value });

  return (
    <div className="space-y-3">
      <textarea
        aria-label="Prompt"
        value={value.prompt}
        onChange={handlePromptChange}
        placeholder="e.g. One of these is how rule 3 was written at eleven o'clock."
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={2}
      />
      <ul className="space-y-2">
        {value.variants.map((text, index) => (
          <li key={index} className="flex items-center gap-2">
            <input
              type="radio"
              name="correct-variant"
              aria-label={`Wording ${index + 1} is the original`}
              checked={value.correctIndex === index}
              onChange={() => onChange({ ...value, correctIndex: index })}
            />
            <Input
              aria-label={`Wording ${index + 1}`}
              value={text}
              onChange={(event) => handleVariantChange(index, event.target.value)}
            />
            <Button
              type="button"
              variant="danger"
              size="sm"
              disabled={value.variants.length <= 2}
              onClick={() => handleVariantRemove(index)}
              aria-label={`Remove wording ${index + 1}`}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={!canAddVariant}
        onClick={handleAddVariant}
      >
        Add wording
      </Button>
      <WindowSlider
        seconds={value.windowSeconds}
        onChange={(windowSeconds) => onChange({ ...value, windowSeconds })}
      />
      <ResultSelect
        label="Result when correct"
        value={value.resultCorrect}
        choices={resultChoices}
        onChange={(resultCorrect) => onChange({ ...value, resultCorrect })}
      />
      <ResultSelect
        label="Result when wrong"
        value={value.resultWrong}
        choices={resultChoices}
        onChange={(resultWrong) => onChange({ ...value, resultWrong })}
      />
      <ResultSelect
        label="Result when time runs out"
        value={value.resultTimeout}
        choices={resultChoices}
        onChange={(resultTimeout) => onChange({ ...value, resultTimeout })}
      />
    </div>
  );
};
