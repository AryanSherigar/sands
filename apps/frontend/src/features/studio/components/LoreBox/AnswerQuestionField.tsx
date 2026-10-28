import React, { useId } from "react";
import { getTextareaRows } from "../../lib/loreBoxLayout";
import { getAnswer } from "../../lib/loreDocument";
import type { QuestionFieldProps } from "./LoreBox.types";

export const AnswerQuestionField: React.FC<
  Pick<QuestionFieldProps, "question" | "document" | "onAnswer">
> = ({ question, document, onAnswer }) => {
  const fieldId = useId();
  const answer = getAnswer(document, question.id);

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>): void =>
    onAnswer(question, event.target.value);

  return (
    <div className="space-y-1">
      <label htmlFor={fieldId} className="block text-meta text-content-muted">
        {question.prompt}
      </label>
      <textarea
        id={fieldId}
        value={answer}
        rows={getTextareaRows(answer) - 1}
        onChange={handleChange}
        className="w-full resize-y rounded-sm border border-border-strong bg-surface-inset px-3 py-2 text-sm text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
      />
    </div>
  );
};
