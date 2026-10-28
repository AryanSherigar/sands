import { usePlayStore } from "../stores/play.store";

/**
 * Submits a check's roll/decline resolution to TRS.
 *
 * Mirrors useMinigameResult: the actual SSE plumbing lives in
 * play.store.ts (submitCheckResolution reuses the same _startTurnStream
 * machinery submitTurn uses), this hook is just the component-facing
 * entrypoint CheckPromptOverlay calls.
 */
export function useCheckResolution() {
  const submit = usePlayStore((s) => s.submitCheckResolution);
  const revealAnimation = usePlayStore((s) => s.revealCheckAnimation);
  return { submit, revealAnimation };
}
