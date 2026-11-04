import { useNavigate } from "react-router-dom";
import { StrategyEndingOverlay } from "./StrategyEndingOverlay";
import type { StrategyEndingGateProps } from "./StrategyEndingGate.types";

const DISCOVER_PATH = "/discover";

export const StrategyEndingGate = ({ ending, scenarioId, onReadLegacy }: StrategyEndingGateProps) => {
  const navigate = useNavigate();
  const handleReturnToScenario = () => navigate(scenarioId ? `/scenario/${scenarioId}` : DISCOVER_PATH);
  const handleReplay = () => navigate(scenarioId ? `/setup/${scenarioId}` : DISCOVER_PATH);

  return (
    <StrategyEndingOverlay
      ending={ending}
      onReadLegacy={onReadLegacy}
      onReturnToScenario={handleReturnToScenario}
      onReplay={handleReplay}
    />
  );
};
