import type { StrategyEpilogueStatus } from "../../hooks/useStrategyEpilogue";

export interface BookClosingEntryProps {
  narration: string;
  status: StrategyEpilogueStatus;
  errorMessage: string | null;
  onRetry: () => void;
}
