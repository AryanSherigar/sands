import type { StrategyDispatchView } from "../../../types/simulation.types";

export interface DispatchEntryProps {
  dispatch: StrategyDispatchView;
  streamedText: string | null;
  isStreaming: boolean;
  isDegraded: boolean;
  onRead: (dispatch: StrategyDispatchView) => void;
}
