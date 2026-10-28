import type React from "react";
import type { InProgressSummary } from "../../types/scenarioPage.types";
import type { ScenarioDetailResponse } from "../../types/scenario";

export interface ScenarioBannerHeroProps {
  scenario: ScenarioDetailResponse;
  reviewCount: number;
  averageRating: number;
  inProgress: InProgressSummary;
  isOwner: boolean;
  isDraft: boolean;
  isBookmarked: boolean;
  isTogglingBookmark: boolean;
  isStartingPlaytest: boolean;
  actionsRef: React.Ref<HTMLDivElement>;
  onToggleBookmark: () => void;
  onShare: () => void;
  onPlaytest: () => void;
}
