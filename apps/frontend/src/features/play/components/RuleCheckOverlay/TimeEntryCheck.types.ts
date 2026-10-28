import type {
  ActiveRuleCheck,
  CheckReportPayload,
} from "@/shared/types/check.types";

export interface TimeEntryCheckProps {
  check: ActiveRuleCheck;
  remainingMs: number;
  isSubmitting: boolean;
  isUntimed: boolean;
  isLocked: boolean;
  onReport: (report: CheckReportPayload, actionLabel: string) => void;
}
