import type { UserPlaythroughSummary } from "../../types/profile.types";

export interface CampaignCardProps {
  campaign: UserPlaythroughSummary;
  onAbandon: (playthroughId: string) => void;
  isAbandoning?: boolean;
}

export interface CampaignStatusProps {
  campaign: UserPlaythroughSummary;
}

export interface CampaignAbandonControlProps {
  onConfirm: () => void;
  isAbandoning: boolean;
}
