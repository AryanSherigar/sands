import type { CouncilDialogueLine } from "../../../lib/proclamation-lines";

export interface ProclamationTranscriptProps {
  lines: CouncilDialogueLine[];
  isStreaming: boolean;
}
