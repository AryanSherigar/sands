import type { SceneExchange } from "../../../types/scene.types";

export interface SceneTranscriptProps {
  exchanges: SceneExchange[];
  leaderName: string;
  pendingPlayerText: string | null;
  streamingReply: string;
}
