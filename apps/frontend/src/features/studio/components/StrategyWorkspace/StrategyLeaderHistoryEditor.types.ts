import type { StrategyLeader, StrategyFields } from "../../types/strategyDocument.types";

export interface StrategyLeaderHistoryEditorProps {
  leader: StrategyLeader;
  factionName: string;
  onEdit: (recipe: (current: StrategyFields) => StrategyFields) => void;
}
