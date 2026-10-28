import { ShiftClockBadge } from "@/shared/components/status-hud/ShiftClockBadge";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import { formatClock } from "@/shared/lib/hud/formatClock";
import { glitchedClock } from "@/shared/lib/hud/glitchedClock";
import { getStateValue } from "@/shared/lib/hud/readDisplayHints";
import { usePlayStore } from "../../stores/play.store";

const STATUS_HUD_TOOL_KEY = "status_hud";

/**
 * The shift clock for a scenario that switched on the Status HUD tool.
 * Renders only when the tool is on and the creator marked a clock field; the
 * widget stays hidden until that field has a number to show. Safe to mount
 * unconditionally in the header. Meters and the tension tier live in
 * `StatusHudStripContainer`.
 */
export function StatusHudContainer() {
  const clockHint = usePlayStore((s) => s.playthrough?.hud_hints?.clock);
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id ?? "");
  const isHudEnabled = usePlayStore(
    (s) => s.playthrough?.enabled_tools?.includes(STATUS_HUD_TOOL_KEY) ?? false,
  );
  const minutes = usePlayStore((s) =>
    clockHint && s.playthrough?.state
      ? getStateValue(s.playthrough.state, clockHint.path)
      : undefined,
  );
  const glitchSourceValue = usePlayStore((s) =>
    clockHint?.hint.glitch && s.playthrough?.state
      ? getStateValue(s.playthrough.state, clockHint.hint.glitch.source)
      : undefined,
  );
  const isMotionReduced = useIsMotionReduced();

  if (!isHudEnabled || !clockHint || typeof minutes !== "number") return null;

  const glitchMinute = glitchedClock({
    playthroughId,
    displayedMinutes: Math.floor(minutes),
    glitch: clockHint.hint.glitch,
    sourceValue: glitchSourceValue,
  });

  return (
    <ShiftClockBadge
      label={clockHint.hint.label}
      time={formatClock(
        minutes,
        clockHint.hint.start,
        clockHint.hint.format,
        glitchMinute ?? undefined,
      )}
      isGlitched={glitchMinute !== null}
      shouldAnimate={!isMotionReduced}
    />
  );
}
