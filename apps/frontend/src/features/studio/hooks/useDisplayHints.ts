import { useMemo } from "react";
import { readDisplayHints } from "@/shared/lib/hud/readDisplayHints";
import type { DisplayHint } from "@/shared/types/display-hints.types";
import { patchFieldAtPath } from "../lib/schemaPatch";
import { useScenario } from "./useScenario";

// The one place the HUD and Atmosphere tabs read and write display hints, so
// the two editors can never hold diverging copies of a meter or tier.
export const useDisplayHints = (scenarioId: string | null) => {
  const { scenario, updateScenario, isUpdating, updateError } =
    useScenario(scenarioId);
  const stateSchema = scenario?.state_schema;
  const hints = useMemo(
    () => readDisplayHints((stateSchema ?? {}) as Record<string, unknown>),
    [stateSchema],
  );

  const saveHint = (path: string, hint: DisplayHint | null): void => {
    if (!stateSchema) return;
    const display = hint === null ? undefined : (hint as unknown as Record<string, unknown>);
    updateScenario({
      state_schema: patchFieldAtPath(stateSchema, path, { display }),
    });
  };

  return {
    stateSchema: stateSchema ?? {},
    hints,
    saveHint,
    isSaving: isUpdating,
    error: updateError,
  };
};
