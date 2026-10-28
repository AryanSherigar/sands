import React, { useState } from "react";
import { Modal } from "@/shared/components/ui/Modal";
import { RuleCheckPrompt } from "@/shared/components/rule-check/RuleCheckPrompt";
import { MS_PER_SECOND } from "../../constants/ruleCheck";
import { RuleCheckPreviewProps } from "./RuleCheckPreview.types";

const VARIANT_ID_PREFIX = "v";

export const RuleCheckPreview: React.FC<RuleCheckPreviewProps> = ({
  state,
  onClose,
}) => {
  const [chosenLabel, setChosenLabel] = useState<string | null>(null);
  const isRecall = state.kind === "recall";
  const prompt = isRecall ? state.recall.prompt : state.timed.prompt;
  const seconds = isRecall ? state.recall.windowSeconds : state.timed.windowSeconds;
  const options = isRecall
    ? state.recall.variants.map((text, index) => ({
        id: `${VARIANT_ID_PREFIX}${index}`,
        label: text,
      }))
    : state.timed.options.map((option) => ({ id: option.id, label: option.label }));

  const handleChoose = (optionId: string): void => {
    const chosen = options.find((option) => option.id === optionId);
    setChosenLabel(chosen?.label ?? optionId);
  };

  return (
    <Modal isOpen onClose={onClose} title="Preview prompt">
      <RuleCheckPrompt
        prompt={prompt}
        options={options}
        remainingMs={seconds * MS_PER_SECOND}
        windowMs={seconds * MS_PER_SECOND}
        isSubmitting={false}
        isRecall={isRecall}
        onChoose={handleChoose}
      />
      <p role="status" className="mt-3 text-xs text-content-faint">
        {chosenLabel
          ? `Chosen: ${chosenLabel}. Preview only, nothing is saved or sent.`
          : "Preview only, nothing is saved or sent."}
      </p>
    </Modal>
  );
};
