import { StatusHud } from "@/shared/components/status-hud/StatusHud";
import { MeterBarProps } from "@/shared/components/status-hud/MeterBar.types";
import { TierPipsProps } from "@/shared/components/status-hud/TierPips.types";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import { getStateValue } from "@/shared/lib/hud/readDisplayHints";
import { resolveMeterTier } from "@/shared/lib/hud/resolveMeterTier";
import { HudHints } from "@/shared/types/display-hints.types";
import { usePlayStore } from "../../stores/play.store";
import { StatusHudStripContainerProps } from "./StatusHudStripContainer.types";

const STATUS_HUD_TOOL_KEY = "status_hud";

const readMeters = (
  hints: HudHints,
  state: Record<string, unknown>,
  shouldAnimate: boolean,
): MeterBarProps[] =>
  hints.meters.flatMap(({ path, hint }) => {
    const value = getStateValue(state, path);
    if (typeof value !== "number") return [];
    return [
      {
        label: hint.label,
        value,
        clampMin: hint.clamp_min,
        clampMax: hint.clamp_max,
        tierName: resolveMeterTier(hint.tiers, value),
        shouldAnimate,
      },
    ];
  });

const readTier = (
  hints: HudHints,
  state: Record<string, unknown>,
): TierPipsProps | null => {
  if (!hints.tier) return null;
  const value = getStateValue(state, hints.tier.path);
  if (typeof value !== "string") return null;
  return { label: hints.tier.hint.label, options: hints.tier.options, value };
};

/**
 * Meters and the tension tier for a scenario with the Status HUD tool on, in a
 * thin strip under the header. Renders nothing when the tool is off, when no
 * meter or tier has a value yet, or when the creator declared none.
 */
export function StatusHudStripContainer({
  themeClassName = "",
}: StatusHudStripContainerProps) {
  const hints = usePlayStore((s) => s.playthrough?.hud_hints);
  const state = usePlayStore((s) => s.playthrough?.state);
  const isHudEnabled = usePlayStore(
    (s) => s.playthrough?.enabled_tools?.includes(STATUS_HUD_TOOL_KEY) ?? false,
  );
  const isMotionReduced = useIsMotionReduced();

  if (!isHudEnabled || !hints || !state) return null;

  const meters = readMeters(hints, state, !isMotionReduced);
  const tier = readTier(hints, state);
  if (meters.length === 0 && !tier) return null;

  return (
    <div
      className={`status-hud-strip border-b px-4 py-1.5 backdrop-blur-md ${themeClassName}`}
    >
      <StatusHud meters={meters} tier={tier} />
    </div>
  );
}
