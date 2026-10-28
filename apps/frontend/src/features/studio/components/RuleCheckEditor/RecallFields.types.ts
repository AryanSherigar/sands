import type { RecallFormState } from "./ruleCheckFormState";

export interface RecallFieldsProps {
  value: RecallFormState;
  resultChoices: string[];
  onChange: (next: RecallFormState) => void;
}
