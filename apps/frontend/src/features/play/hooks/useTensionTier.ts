import { useMemo } from "react";
import { getStateValue } from "@/shared/lib/hud/readDisplayHints";
import { usePlayStore } from "../stores/play.store";

const ATMOSPHERE_TOOL_KEY = "atmosphere";
const STATUS_HUD_TOOL_KEY = "status_hud";

export interface TensionReading {
  value: string;
  index: number;
  count: number;
  moodMap: Record<string, string> | undefined;
}

// The tension tier is the creator's `tier` display field. Reader effects and
// tension audio read it only when both Atmosphere and Status HUD are on.
export function useTensionTier(): TensionReading | null {
  const areToolsOn = usePlayStore((s) => {
    const tools = s.playthrough?.enabled_tools;
    return (
      (tools?.includes(ATMOSPHERE_TOOL_KEY) ?? false) &&
      (tools?.includes(STATUS_HUD_TOOL_KEY) ?? false)
    );
  });
  const tier = usePlayStore((s) => s.playthrough?.hud_hints?.tier);
  const value = usePlayStore((s) =>
    tier && s.playthrough?.state
      ? getStateValue(s.playthrough.state, tier.path)
      : undefined,
  );

  return useMemo(() => {
    if (!areToolsOn || !tier || typeof value !== "string") return null;
    const index = tier.options.indexOf(value);
    if (index < 0) return null;
    return {
      value,
      index,
      count: tier.options.length,
      moodMap: tier.hint.mood_map,
    };
  }, [areToolsOn, tier, value]);
}
