import { getStateValue } from "@/shared/lib/hud/readDisplayHints";
import {
  resolveSanityBand,
  SanityBand,
} from "@/shared/lib/typography/resolveSanityBand";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { MeterEffects } from "@/shared/types/display-hints.types";
import { usePlayStore } from "../stores/play.store";

const ATMOSPHERE_TOOL_KEY = "atmosphere";
const STATUS_HUD_TOOL_KEY = "status_hud";

export interface SanityBandReading {
  band: SanityBand;
  value: number | null;
  effects: MeterEffects | undefined;
}

const NO_READING: SanityBandReading = {
  band: "none",
  value: null,
  effects: undefined,
};

// The meter that drives reader effects is the one meter that defines `effects`
// (the Core API allows only one). It reads from state by its dotted path.
export function useSanityBand(): SanityBandReading {
  const areToolsOn = usePlayStore((s) => {
    const tools = s.playthrough?.enabled_tools;
    return (
      (tools?.includes(ATMOSPHERE_TOOL_KEY) ?? false) &&
      (tools?.includes(STATUS_HUD_TOOL_KEY) ?? false)
    );
  });
  const driver = usePlayStore((s) =>
    s.playthrough?.hud_hints?.meters.find((meter) => meter.hint.effects),
  );
  const value = usePlayStore((s) =>
    driver && s.playthrough?.state
      ? getStateValue(s.playthrough.state, driver.path)
      : undefined,
  );
  const shouldReduce = useReaderPreferencesStore((s) => s.reduceSensoryEffects);

  if (!areToolsOn || shouldReduce || !driver || typeof value !== "number") {
    return NO_READING;
  }
  return {
    band: resolveSanityBand(value, driver.hint.effects),
    value,
    effects: driver.hint.effects,
  };
}
