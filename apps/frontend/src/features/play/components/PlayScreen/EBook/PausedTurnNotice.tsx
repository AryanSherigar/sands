import { ALPHA_PAUSED_MESSAGE } from "@/shared/lib/alpha-paused-error";
import { usePlayStore } from "../../../stores/play.store";

export function PausedTurnNotice() {
  const isPaused = usePlayStore((s) => s.is_turn_paused);
  const hasPendingAction = usePlayStore(
    (s) => s.last_client_action_id !== null,
  );
  const retryLastTurn = usePlayStore((s) => s.retryLastTurn);

  if (!isPaused) return null;

  const handleTryAgain = (): void => retryLastTurn();

  return (
    <div
      role="status"
      className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 font-sans text-sm text-content"
    >
      <p>{ALPHA_PAUSED_MESSAGE}</p>
      {hasPendingAction && (
        <button
          type="button"
          onClick={handleTryAgain}
          className="cursor-pointer rounded-xl border border-warning/40 px-3 py-1 font-mono text-xs transition-colors hover:bg-hover-wash"
        >
          Try again
        </button>
      )}
    </div>
  );
}
