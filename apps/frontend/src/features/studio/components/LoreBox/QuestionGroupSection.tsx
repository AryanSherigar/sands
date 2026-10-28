import React from "react";
import type { QuestionGroupSectionProps } from "./LoreBox.types";
import { QuestionField } from "./QuestionField";

export const QuestionGroupSection: React.FC<QuestionGroupSectionProps> = ({
  group,
  isOpen,
  onToggle,
  document,
  pickOptions,
  onAnswer,
  onPick,
}) => (
  <li>
    <button
      type="button"
      aria-expanded={isOpen}
      onClick={onToggle}
      className="w-full rounded-sm px-2 py-1.5 text-left text-meta font-medium text-content hover:bg-white/6"
    >
      {group.name}
    </button>
    {isOpen && (
      <div className="space-y-3 px-2 pt-2 pb-3">
        {group.questions.map((question) => (
          <QuestionField
            key={question.id}
            question={question}
            document={document}
            pickOptions={pickOptions}
            onAnswer={onAnswer}
            onPick={onPick}
          />
        ))}
      </div>
    )}
  </li>
);
