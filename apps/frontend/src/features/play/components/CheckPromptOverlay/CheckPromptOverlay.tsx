import { useEffect } from "react";
import { usePlayStore } from "../../stores/play.store";
import { useCheckResolution } from "../../hooks/useCheckResolution";
import { CHECK_ROLL_ANIMATION_DURATION_MS } from "../../constants/check.constants";

/**
 * Full-screen takeover for a proposed check: the roll/decline prompt, the
 * fixed-duration roll animation, and — once revealed — this same turn's
 * narration streaming in, until the turn commits. Reads active_check from
 * play.store.ts directly (set either by a fresh "check" SSE event or, on
 * reload, from PlaythroughData.pending_check) and renders nothing when none
 * is pending — safe to mount unconditionally on the play surface, mirrors
 * MinigameOverlay.
 *
 * resolved_check_outcome (the actual roll) is deliberately not shown while
 * is_check_animation_pending is still true, even though it may already have
 * arrived over SSE — the animation's whole point is to withhold it until
 * its fixed duration elapses.
 */
export function CheckPromptOverlay() {
  const activeCheck = usePlayStore((s) => s.active_check);
  const isNarrating = usePlayStore((s) => s.is_narrating);
  const isAnimating = usePlayStore((s) => s.is_check_animation_pending);
  const resolvedOutcome = usePlayStore((s) => s.resolved_check_outcome);
  const streamingText = usePlayStore((s) => s.streaming_text);
  const { submit, revealAnimation } = useCheckResolution();

  useEffect(() => {
    if (!isAnimating) return;
    const timer = setTimeout(revealAnimation, CHECK_ROLL_ANIMATION_DURATION_MS);
    return () => clearTimeout(timer);
  }, [isAnimating, revealAnimation]);

  if (!activeCheck) return null;

  const handleRoll = (): void => {
    submit({ check_id: activeCheck.check_id, resolution: "attempt" });
  };
  const handleDecline = (): void => {
    submit({ check_id: activeCheck.check_id, resolution: "decline" });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-6">
      <div className="max-w-md w-full space-y-5 rounded-xl border border-white/20 bg-zinc-950 p-6 text-center text-white">
        <span className="inline-block rounded bg-white/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-zinc-400">
          {activeCheck.check_type} check — DC {activeCheck.difficulty_class}
        </span>

        {!isNarrating && (
          <>
            {activeCheck.reasoning && (
              <p className="text-sm text-zinc-300">{activeCheck.reasoning}</p>
            )}
            <p className="text-sm text-zinc-400">
              Attempt the check, or step back from it.
            </p>
            <div className="flex justify-center gap-3">
              <button
                type="button"
                onClick={handleDecline}
                className="rounded border border-white/20 px-4 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-white"
              >
                Decline
              </button>
              <button
                type="button"
                onClick={handleRoll}
                className="rounded bg-white px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-zinc-200"
              >
                Roll
              </button>
            </div>
          </>
        )}

        {isNarrating && isAnimating && (
          <div className="space-y-3 py-4" role="status" aria-live="assertive">
            <div className="mx-auto text-4xl motion-safe:animate-spin">🎲</div>
            <p className="text-sm text-zinc-300">Rolling...</p>
          </div>
        )}

        {isNarrating && !isAnimating && (
          <div className="space-y-3 text-left" aria-live="polite">
            {resolvedOutcome && (
              <p className="text-center text-sm font-semibold text-zinc-200">
                Rolled {resolvedOutcome.resolved_roll} vs DC{" "}
                {resolvedOutcome.difficulty_class} —{" "}
                {resolvedOutcome.is_success ? "Success" : "Failure"}
              </p>
            )}
            <p className="whitespace-pre-wrap text-sm text-zinc-300">
              {streamingText}
              <span className="animate-pulse">▌</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
