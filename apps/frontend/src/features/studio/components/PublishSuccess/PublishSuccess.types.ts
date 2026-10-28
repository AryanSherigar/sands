import type { AchievementSummary } from "../../types/achievement.types";

export interface PublishSuccessProps {
  scenarioId: string;
  isPublic: boolean;
  achievement: AchievementSummary | null;
  onMakePublic: () => void;
  isMakingPublic: boolean;
  makePublicError: string | null;
}

export interface InvitePeoplePanelProps {
  scenarioId: string;
}

export interface WorldmakerRevealProps {
  achievement: AchievementSummary;
}
