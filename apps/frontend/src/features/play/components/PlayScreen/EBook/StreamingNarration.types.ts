export interface StreamingNarrationProps {
  isFantasy?: boolean;
  chapterNumber: number;
  characterName: string;
  fontClass: string;
  shouldDistort: boolean;
  playthroughId: string;
  onScrollToBottom: (behavior: ScrollBehavior) => void;
}
