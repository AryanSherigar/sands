export interface WelcomeTapeControlsProps {
  isFailed: boolean;
  isReady: boolean;
  isPaused: boolean;
  isMuted: boolean;
  hasCaptions: boolean;
  onRetry: () => void;
  onPlay: () => void;
  onPause: () => void;
  onMute: () => void;
  onCaptions: () => void;
  onSkip: () => void;
}
