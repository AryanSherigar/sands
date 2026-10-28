import type { RuleCheckFormState } from "./ruleCheckFormState";

export interface RuleCheckPreviewProps {
  state: RuleCheckFormState;
  onClose: () => void;
}
