import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { FULL_EDITOR_PARAM, FULL_EDITOR_VALUE } from "../constants/studioFrame";
import { useGuide } from "./useGuide";

export const useOpenFullEditor = (): (() => void) => {
  const { scenarioId } = useGuide();
  const navigate = useNavigate();

  return useCallback((): void => {
    if (!scenarioId) return;
    navigate(`/studio/${scenarioId}/edit?${FULL_EDITOR_PARAM}=${FULL_EDITOR_VALUE}`);
  }, [navigate, scenarioId]);
};
