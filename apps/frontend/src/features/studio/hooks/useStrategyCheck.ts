import { useQuery } from "@tanstack/react-query";
import { checkStrategyScenario } from "../api/strategy.api";
import type { PublishReport } from "../types/strategyDocument.types";

export const useStrategyCheck = (scenarioId: string, contentEditedAt: string | undefined) =>
  useQuery<PublishReport, Error>({
    queryKey: ["strategy-check", scenarioId, contentEditedAt],
    queryFn: () => checkStrategyScenario(scenarioId),
    staleTime: 0,
  });
