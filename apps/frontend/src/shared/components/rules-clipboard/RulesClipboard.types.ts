import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";

export interface RulesClipboardProps {
  rules: RuleSheetItem[];
  duties?: string[];
  isMotionReduced: boolean;
}
