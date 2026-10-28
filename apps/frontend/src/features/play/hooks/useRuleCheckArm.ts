import { useEffect } from "react";
import type { ActiveRuleCheck } from "@/shared/types/check.types";
import { isRuleCheckArmed } from "@/shared/types/check.types";
import { ARM_RETRY_DELAY_MS } from "../constants/ruleCheck.constants";
import { usePlayStore } from "../stores/play.store";
import { readingBeatMs } from "../utils/readingBeat";

/**
 * Asks the server to start the open rule check's clock once a reading beat,
 * sized to the narration that set it up, has passed. Retries until the server
 * accepts, so a dropped request never strands a locked prompt.
 */
export const useRuleCheckArm = (
  check: ActiveRuleCheck | null,
  narrationText: string,
): void => {
  const armRuleCheck = usePlayStore((s) => s.armRuleCheck);
  const checkId = check?.check_id ?? null;
  const shouldArm = check !== null && !isRuleCheckArmed(check);

  useEffect(() => {
    if (!shouldArm || checkId === null) return;
    let timer = window.setTimeout(attempt, readingBeatMs(narrationText));
    let isCancelled = false;

    function attempt(): void {
      armRuleCheck(checkId as string).catch(() => {
        if (isCancelled) return;
        timer = window.setTimeout(attempt, ARM_RETRY_DELAY_MS);
      });
    }

    return () => {
      isCancelled = true;
      window.clearTimeout(timer);
    };
    // The beat is sized once per prompt; later narration edits must not re-time it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldArm, checkId, armRuleCheck]);
};
