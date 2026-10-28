import type { SchemaFieldRef } from "../../lib/stateSchemaFields";
import type {
  RuleCheckCreate,
  RuleCheckResponse,
} from "../../types/ruleCheck.types";
import type { AvailableField } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";

export interface RuleCheckFormProps {
  check: RuleCheckResponse | null;
  availableFields: AvailableField[];
  enumFields: SchemaFieldRef[];
  onSubmit: (payload: RuleCheckCreate) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitError: string | null;
}
