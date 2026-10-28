import type {
  SheetRuleCreate,
  SheetRuleResponse,
} from "../../types/sheetRule.types";

export interface SheetRuleFormProps {
  rule: SheetRuleResponse | null;
  existingKeys: string[];
  nextNumber: number;
  onSubmit: (payload: SheetRuleCreate) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitError: string | null;
}
