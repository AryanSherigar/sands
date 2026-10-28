import React from "react";
import { AnswerQuestionField } from "./AnswerQuestionField";
import type { QuestionFieldProps } from "./LoreBox.types";
import { PickQuestionField } from "./PickQuestionField";

export const QuestionField: React.FC<QuestionFieldProps> = (props) => {
  if (props.question.pick) return <PickQuestionField {...props} />;
  return (
    <AnswerQuestionField
      question={props.question}
      document={props.document}
      onAnswer={props.onAnswer}
    />
  );
};
