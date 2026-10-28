import { useMemo } from "react";
import { buildUnsupportedPathCheck, buildValueOptions } from "../lib/valueOptions";
import type { ValueOption } from "../types/sentence.types";
import { useGuide } from "./useGuide";
import { useGuideCards } from "./useGuideCards";

export interface ValueOptionsState {
  options: ValueOption[];
  isUnsupportedPath: (path: string) => boolean;
  isLoading: boolean;
}

export const useValueOptionsState = (): ValueOptionsState => {
  const { scenario, isLoading: isLoadingScenario } = useGuide();
  const { entities, isLoading: isLoadingCards } = useGuideCards();
  const stateSchema = scenario?.state_schema;
  const options = useMemo(() => buildValueOptions(stateSchema ?? {}, entities), [entities, stateSchema]);

  const isUnsupportedPath = useMemo(
    () => buildUnsupportedPathCheck(stateSchema ?? {}, entities, options),
    [entities, options, stateSchema],
  );

  return { options, isUnsupportedPath, isLoading: isLoadingScenario || isLoadingCards || scenario === null };
};
