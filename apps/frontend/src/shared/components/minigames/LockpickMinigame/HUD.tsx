import { HUDProps } from "./HUD.types";

export function HUD({
  picksRemaining,
  initialPicks,
  cylindersClicked,
  totalCylinders,
  timeRemainingMs,
  durationMs,
}: HUDProps) {
  const timeFraction =
    durationMs > 0 ? Math.max(0, timeRemainingMs / durationMs) : 0;

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col gap-2 p-4">
      {/* Time bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-amber-400 transition-[width] duration-150 ease-linear"
          style={{ width: `${timeFraction * 100}%` }}
        />
      </div>

      <div className="flex items-center justify-between">
        {/* Picks remaining icons */}
        <div className="flex items-center gap-1.5">
          <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Picks:
          </span>
          {Array.from({ length: initialPicks }, (_, index) => (
            <span
              key={index}
              title={`Pick ${index + 1}`}
              className={
                index < picksRemaining
                  ? "h-4 w-1 rounded bg-amber-400 shadow-[0_0_6px_1px_rgba(251,191,36,0.6)]"
                  : "h-4 w-1 rounded bg-white/10"
              }
            />
          ))}
        </div>

        {/* Tumbler cylinders count */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Tumblers:
          </span>
          <span className="text-xs font-bold text-amber-400">
            {cylindersClicked} / {totalCylinders}
          </span>
        </div>
      </div>
    </div>
  );
}
