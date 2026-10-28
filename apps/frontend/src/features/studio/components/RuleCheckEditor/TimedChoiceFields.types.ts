import type { TimedFormState } from "./ruleCheckFormState";

export interface TimedChoiceFieldsProps {
  value: TimedFormState;
  resultChoices: string[];
  onChange: (next: TimedFormState) => void;
}
