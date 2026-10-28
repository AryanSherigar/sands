import React from "react";
import { TimeEntryPrompt } from "@/shared/components/rule-check/TimeEntryPrompt";
import type { ActiveRuleCheck } from "@/shared/types/check.types";
import {
  DEFAULT_TIME_ENTRY_ENTER_LABEL,
  DEFAULT_TIME_ENTRY_REJECT_LABEL,
  TIME_ENTRY_ENTER_OPTION_ID,
  TIME_ENTRY_REJECT_OPTION_ID,
} from "../../constants/ruleCheck.constants";
import { TimeEntryCheckProps } from "./TimeEntryCheck.types";

const optionLabelOf = (
  check: ActiveRuleCheck,
  optionId: string,
  fallback: string,
): string =>
  check.options.find((option) => option.id === optionId)?.label ?? fallback;

export const TimeEntryCheck: React.FC<TimeEntryCheckProps> = ({
  check,
  remainingMs,
  isSubmitting,
  isUntimed,
  isLocked,
  onReport,
}) => {
  const rejectLabel = optionLabelOf(
    check,
    TIME_ENTRY_REJECT_OPTION_ID,
    DEFAULT_TIME_ENTRY_REJECT_LABEL,
  );

  const handleEnter = (entryText: string): void => {
    onReport(
      {
        check_id: check.check_id,
        choice_id: TIME_ENTRY_ENTER_OPTION_ID,
        entry_text: entryText,
      },
      entryText,
    );
  };

  const handleReject = (): void => {
    onReport(
      { check_id: check.check_id, choice_id: TIME_ENTRY_REJECT_OPTION_ID },
      rejectLabel,
    );
  };

  return (
    <TimeEntryPrompt
      prompt={check.prompt}
      toldLabel={check.told_label ?? null}
      wallLabel={check.wall_label ?? null}
      enterLabel={optionLabelOf(
        check,
        TIME_ENTRY_ENTER_OPTION_ID,
        DEFAULT_TIME_ENTRY_ENTER_LABEL,
      )}
      rejectLabel={rejectLabel}
      remainingMs={remainingMs}
      windowMs={check.window_ms}
      isSubmitting={isSubmitting}
      isUntimed={isUntimed}
      isDocked
      isLocked={isLocked}
      onEnter={handleEnter}
      onReject={handleReject}
    />
  );
};
