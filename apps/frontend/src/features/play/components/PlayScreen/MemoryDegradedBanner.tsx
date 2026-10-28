import { useRetryMemory } from "../../hooks/useRetryMemory";
import { usePlayStore } from "../../stores/play.store";

export function MemoryDegradedBanner() {
  const reasons = usePlayStore((s) => s.memory_degraded_reasons);
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id);
  const isSpectator = usePlayStore((s) => s.playthrough?.is_spectator);
  const { mutate, isPending, isError } = useRetryMemory(playthroughId ?? "");

  if (reasons.length === 0 || !playthroughId || isSpectator) return null;

  return (
    <div
      role="status"
      className="relative z-20 flex flex-wrap items-center justify-between gap-2 border-t border-warning/40 bg-warning/10 px-4 py-2 text-sm text-content"
    >
      <p>
        {isError
          ? "Couldn't reach story memory. You can keep playing and try again."
          : "Some story memory is catching up — immersion may be reduced."}
      </p>
      <button
        type="button"
        onClick={() => mutate()}
        disabled={isPending}
        className="rounded-xl border border-warning/40 px-3 py-1 font-mono text-xs transition-colors hover:bg-hover-wash disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer"
      >
        {isPending ? "Retrying…" : "Retry memory"}
      </button>
    </div>
  );
}
