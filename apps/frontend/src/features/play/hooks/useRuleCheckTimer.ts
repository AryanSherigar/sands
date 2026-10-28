import { useEffect, useRef, useState } from "react";
import { ActiveRuleCheck } from "@/shared/types/check.types";

const TICK_INTERVAL_MS = 100;

const remainingOf = (check: ActiveRuleCheck): number =>
  Math.max(
    0,
    check.initial_remaining_ms - (Date.now() - check.started_at_client_ms),
  );

// Counts down the time left on an open rule check and calls `onExpire` once
// when it reaches zero. The server judges lateness itself; this timer only
// decides when the client reports that it ran out.
export const useRuleCheckTimer = (
  check: ActiveRuleCheck | null,
  onExpire: () => void,
): number => {
  const [remainingMs, setRemainingMs] = useState(0);
  const onExpireRef = useRef(onExpire);
  const checkId = check?.check_id ?? null;
  const startedAt = check?.started_at_client_ms ?? null;

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    if (!check) {
      setRemainingMs(0);
      return;
    }
    let hasExpired = false;
    const tick = (): void => {
      const remaining = remainingOf(check);
      setRemainingMs(remaining);
      if (remaining === 0 && !hasExpired) {
        hasExpired = true;
        window.clearInterval(timer);
        onExpireRef.current();
      }
    };
    const timer = window.setInterval(tick, TICK_INTERVAL_MS);
    setRemainingMs(remainingOf(check));
    return () => window.clearInterval(timer);
    // The check object is identified by its id and start time; a re-created
    // object for the same prompt must not restart the countdown.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkId, startedAt]);

  return remainingMs;
};
