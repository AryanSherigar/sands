export interface NegotiationReadingChamberProps {
  situation: string;
  transcript: Array<{ sequence: number; player_text: string; leader_text: string }>;
  leaderName: string;
  pendingPlayerText?: string | null;
  streamingReply?: string;
  isStreaming?: boolean;
  warningMessage?: string | null;
}
