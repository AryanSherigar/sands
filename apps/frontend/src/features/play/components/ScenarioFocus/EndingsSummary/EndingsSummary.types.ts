import type { ScenarioEndingsResponse } from "../../../types/scenario";

export interface EndingsSummaryProps {
  endings: ScenarioEndingsResponse | undefined;
  isError: boolean;
  onRetry: () => void;
}
