import type { CheckOptionShape } from "../../types/ruleCheck.types";

export interface OptionRowProps {
  index: number;
  option: CheckOptionShape;
  resultChoices: string[];
  canRemove: boolean;
  onChange: (index: number, option: CheckOptionShape) => void;
  onRemove: (index: number) => void;
}
