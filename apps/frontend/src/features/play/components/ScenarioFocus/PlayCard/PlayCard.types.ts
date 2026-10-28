import type { InProgressSummary } from "../../../types/scenarioPage.types";

export interface PlayCardProps {
  scenarioId: string;
  title: string;
  playCount: number;
  isDraft: boolean;
  isStartingPlaytest: boolean;
  inProgress: InProgressSummary;
  onPlaytest: () => void;
}
