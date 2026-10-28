import type { SetupInputField } from "@/shared/types/scenario.types";
import type { PlaytestTurn } from "../../stores/playtest.store";

export interface PlaytestSetupFormProps {
  fields: SetupInputField[];
  isStarting: boolean;
  onStart: (values: Record<string, unknown>) => void;
}

export interface PlaytestToolbarProps {
  isBusy: boolean;
  onRestart: () => void;
  onEnd: () => void;
}

export interface PlaytestTranscriptProps {
  openingText: string;
  turns: PlaytestTurn[];
  streamingNarration: string;
  isStreaming: boolean;
}

export interface PlaytestActionBoxProps {
  isDisabled: boolean;
  onSubmit: (actionText: string) => void;
}

export interface PlaytestStaleBannerProps {
  onKeepPlaying: () => void;
}

export interface PlaytestMessageProps {
  message: string;
  actionLabel: string;
  onAction: () => void;
  isAlert?: boolean;
}
