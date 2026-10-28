import { RuleCheckPrompt } from "@/shared/components/rule-check/RuleCheckPrompt";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import {
  isRuleCheckArmed,
  type ActiveRuleCheck,
  type CheckReportPayload,
  type RuleCheckOptionView,
} from "@/shared/types/check.types";
import { TimeEntryCheck } from "./TimeEntryCheck";
import { useRuleCheckArm } from "../../hooks/useRuleCheckArm";
import { usePageHiddenGrace } from "../../hooks/usePageHiddenGrace";
import { useRuleCheckTimer } from "../../hooks/useRuleCheckTimer";
import { usePlayStore } from "../../stores/play.store";
import {
  DEFAULT_HIDDEN_GRACE_MS,
  RULE_CHECK_TIMEOUT_ACTION_TEXT,
} from "../../constants/ruleCheck.constants";

const RECALL_KIND = "recall";
const TIME_ENTRY_KIND = "time_entry";

const choicesOf = (check: ActiveRuleCheck): RuleCheckOptionView[] =>
  check.kind === RECALL_KIND
    ? (check.variants ?? []).map((variant) => ({
        id: variant.id,
        label: variant.text,
      }))
    : check.options;

/**
 * Prompt docked under the narration for a rule check (timed prompt, recall
 * test or visitor log) the server opened. It starts locked so the narration that
 * set it up can be read; after a reading beat the server starts its clock. Reads active_rule_check from play.store.ts (set by a fresh
 * `check` event or resumed on reload) and renders nothing when none is open, so
 * it can be mounted unconditionally beside CheckPromptOverlay. The client only
 * reports the chosen option, that its timer ran out, and whether the tab was
 * hidden; the server judges lateness and decides the result. With "Reduce
 * sensory effects" on the prompt is untimed and the report says so.
 */
export function RuleCheckOverlay() {
  const activeCheck = usePlayStore((s) => s.active_rule_check);
  const isSubmitting = usePlayStore((s) => s.is_rule_check_submitting);
  const isSpectator = usePlayStore((s) => s.playthrough?.is_spectator ?? false);
  const submitCheckReport = usePlayStore((s) => s.submitCheckReport);
  const isUntimed = useReaderPreferencesStore((s) => s.reduceSensoryEffects);
  const lastNarration = usePlayStore(
    (s) => s.playthrough?.turns.at(-1)?.narration_text ?? "",
  );
  const isArmed = activeCheck !== null && isRuleCheckArmed(activeCheck);
  useRuleCheckArm(isSpectator ? null : activeCheck, lastNarration);
  const wasHidden = usePageHiddenGrace(
    isArmed && !isSpectator && !isUntimed,
    activeCheck?.hidden_grace_ms ?? DEFAULT_HIDDEN_GRACE_MS,
  );

  const withFlags = (report: CheckReportPayload): CheckReportPayload => ({
    ...report,
    ...(wasHidden ? { was_hidden: true } : {}),
    ...(isUntimed ? { is_untimed: true } : {}),
  });

  const handleReport = (report: CheckReportPayload, label: string): void => {
    submitCheckReport(withFlags(report), label);
  };

  const handleExpire = (): void => {
    if (!activeCheck || isUntimed) return;
    submitCheckReport(
      withFlags({ check_id: activeCheck.check_id, timed_out: true }),
      RULE_CHECK_TIMEOUT_ACTION_TEXT,
    );
  };
  const remainingMs = useRuleCheckTimer(
    isSpectator || isUntimed || !isArmed ? null : activeCheck,
    handleExpire,
  );

  if (!activeCheck || isSpectator) return null;

  if (activeCheck.kind === TIME_ENTRY_KIND) {
    return (
      <TimeEntryCheck
        check={activeCheck}
        remainingMs={remainingMs}
        isSubmitting={isSubmitting}
        isUntimed={isUntimed}
        isLocked={!isArmed}
        onReport={handleReport}
      />
    );
  }

  const choices = choicesOf(activeCheck);
  const handleChoose = (choiceId: string): void => {
    const choice = choices.find((item) => item.id === choiceId);
    submitCheckReport(
      withFlags({ check_id: activeCheck.check_id, choice_id: choiceId }),
      choice?.label ?? choiceId,
    );
  };

  return (
    <RuleCheckPrompt
      prompt={activeCheck.prompt}
      options={choices}
      remainingMs={remainingMs}
      windowMs={activeCheck.window_ms}
      isSubmitting={isSubmitting}
      isUntimed={isUntimed}
      isDocked
      isLocked={!isArmed}
      isRecall={activeCheck.kind === RECALL_KIND}
      onChoose={handleChoose}
    />
  );
}
