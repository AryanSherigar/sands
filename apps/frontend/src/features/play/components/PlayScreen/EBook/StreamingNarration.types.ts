export interface StreamingNarrationProps {
  chapterNumber: number;
  characterName: string;
  fontClass: string;
  shouldDistort: boolean;
  playthroughId: string;
  onScrollToBottom: (behavior: ScrollBehavior) => void;
}
