import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export interface UseSurpriseMeResult {
  isDisabled: boolean;
  handleSurprise: () => void;
}

export const useSurpriseMe = (
  scenarios: ScenarioSummaryResponse[],
): UseSurpriseMeResult => {
  const navigate = useNavigate();
  const playable = useMemo(
    () => scenarios.filter((scenario) => scenario.status !== "archived"),
    [scenarios],
  );
  const isDisabled = playable.length === 0;

  const handleSurprise = useCallback((): void => {
    if (playable.length === 0) return;
    const pick = playable[Math.floor(Math.random() * playable.length)];
    navigate(`/scenario/${pick.scenario_id}`);
  }, [navigate, playable]);

  return { isDisabled, handleSurprise };
};
