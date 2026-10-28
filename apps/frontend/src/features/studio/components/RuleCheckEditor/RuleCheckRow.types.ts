import type { RuleCheckResponse } from "../../types/ruleCheck.types";

export interface RuleCheckRowProps {
  check: RuleCheckResponse;
  index: number;
  total: number;
  onEdit: (check: RuleCheckResponse) => void;
  onDelete: (checkId: string) => void;
  onMove: (index: number, offset: number) => void;
}
