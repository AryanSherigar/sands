import React, { useId } from "react";
import { Select } from "@/shared/components/ui/Select";
import { CARD_KIND_PICK_PLACEHOLDERS } from "../../constants/cardKinds";
import type { GuideQuestion, PickOption } from "../../types/guide.types";
import type { QuestionFieldProps } from "./LoreBox.types";

const getAvailableChoices = (
  question: GuideQuestion,
  document: QuestionFieldProps["document"],
  pickOptions: PickOption[],
): PickOption[] => {
  const wantedKind = question.pick?.kind ?? "any";
  const pickedNames = document.blocks
    .filter((block) => block.question_id === question.id)
    .map((block) => block.text.toLowerCase());
  return pickOptions.filter(
    (option) =>
      (wantedKind === "any" || option.kind === wantedKind) &&
      !pickedNames.includes(option.name.toLowerCase()),
  );
};

export const PickQuestionField: React.FC<QuestionFieldProps> = ({
  question,
  document,
  pickOptions,
  onPick,
}) => {
  const fieldId = useId();
  const choices = getAvailableChoices(question, document, pickOptions);
  const placeholder = CARD_KIND_PICK_PLACEHOLDERS[question.pick?.kind ?? "any"];

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    const chosen = choices.find((option) => option.id === event.target.value);
    if (chosen) onPick(question, chosen);
  };

  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="block text-meta text-content-muted">
        {question.prompt}
      </label>
      <Select
        id={fieldId}
        value=""
        onChange={handleChange}
        options={[
          { value: "", label: placeholder },
          ...choices.map((option) => ({ value: option.id, label: option.name })),
        ]}
      />
    </div>
  );
};
