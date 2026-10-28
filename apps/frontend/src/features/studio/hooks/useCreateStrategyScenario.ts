import { useMutation } from "@tanstack/react-query";
import { createScenario } from "../api/scenarios.api";
import { STRATEGY_SCENARIO_TITLE } from "../constants/strategyAuthoring";
import type { ScenarioResponse } from "../types/scenario.types";

const EMPTY_STRATEGY_DOCUMENT = { schema_version: 1 };

export const useCreateStrategyScenario = () =>
  useMutation<ScenarioResponse, Error>({
    mutationFn: () =>
      createScenario({
        title: STRATEGY_SCENARIO_TITLE,
        mode: "strategy",
        complexity_tier: "master",
        visibility: "private",
        strategy_document: EMPTY_STRATEGY_DOCUMENT,
      }),
  });
