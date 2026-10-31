import { useMutation } from "@tanstack/react-query";
import { createScenario } from "../api/scenarios.api";
import { STRATEGY_SCENARIO_TITLE, STUDIO_DEFAULT_END_YEAR } from "../constants/strategyAuthoring";
import type { ScenarioResponse } from "../types/scenario.types";

const NEW_STRATEGY_DOCUMENT = { schema_version: 1, tuning: { end_year: STUDIO_DEFAULT_END_YEAR } };

export const useCreateStrategyScenario = () =>
  useMutation<ScenarioResponse, Error>({
    mutationFn: () =>
      createScenario({
        title: STRATEGY_SCENARIO_TITLE,
        mode: "strategy",
        complexity_tier: "master",
        visibility: "private",
        strategy_document: NEW_STRATEGY_DOCUMENT,
      }),
  });
