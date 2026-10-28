export interface HeroActionsProps {
  scenarioId: string;
  isOwner: boolean;
  isDraft: boolean;
  isBookmarked: boolean;
  isTogglingBookmark: boolean;
  isStartingPlaytest: boolean;
  onToggleBookmark: () => void;
  onShare: () => void;
  onPlaytest: () => void;
}
