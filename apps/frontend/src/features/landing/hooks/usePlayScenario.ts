import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { SETUP_PATH_PREFIX } from "../constants/landing.constants";

export const usePlayScenario = (
  scenarioId: string,
): (() => Promise<void>) => {
  const navigate = useNavigate();
  const requireAuth = useRequireAuth("setup");

  return useCallback(async (): Promise<void> => {
    if (await requireAuth()) navigate(`${SETUP_PATH_PREFIX}/${scenarioId}`);
  }, [requireAuth, navigate, scenarioId]);
};
