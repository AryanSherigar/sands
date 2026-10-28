import type { SheetRuleResponse } from "../../types/sheetRule.types";

export interface SheetRuleRowProps {
  rule: SheetRuleResponse;
  index: number;
  total: number;
  onEdit: (rule: SheetRuleResponse) => void;
  onDelete: (ruleId: string) => void;
  onMove: (index: number, offset: number) => void;
}
