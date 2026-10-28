import { useState } from "react";
import { IntakeSurvey } from "@/shared/components/alpha-survey/IntakeSurvey/IntakeSurvey";
import { INTAKE_DONE_STORAGE_PREFIX } from "@/shared/constants/alpha-survey";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { logEvent } from "@/shared/lib/logger";

const EVENT_STORAGE_FAILED = "alpha_intake_storage_failed";

function readIsDone(storageKey: string): boolean {
  try {
    return localStorage.getItem(storageKey) === "true";
  } catch (error) {
    logEvent("warning", EVENT_STORAGE_FAILED, { error: String(error) });
    return false;
  }
}

function writeIsDone(storageKey: string): void {
  try {
    localStorage.setItem(storageKey, "true");
  } catch (error) {
    // NOTE: The server rejects a second intake, so a lost flag only re-asks.
    logEvent("warning", EVENT_STORAGE_FAILED, { error: String(error) });
  }
}

/** Shows the intake survey once per tester, right after consent. Mounted only
 * while collection is on. */
export function AlphaIntakeGate() {
  const userId = useAuthStore((state) => state.user?.user_id);
  const storageKey = `${INTAKE_DONE_STORAGE_PREFIX}${userId ?? "unknown"}`;
  const [isDone, setIsDone] = useState(() => readIsDone(storageKey));

  if (!userId) return null;

  const handleClose = (): void => {
    writeIsDone(storageKey);
    setIsDone(true);
  };

  return <IntakeSurvey isOpen={!isDone} onClose={handleClose} />;
}
