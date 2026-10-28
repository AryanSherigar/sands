import type { WelcomePlayback } from "../../utils/welcomePlayback";

export interface WelcomeTapePictureProps {
  urls: string[];
  time: number;
  isPaused: boolean;
  hasCaptions: boolean;
  characterName: string;
  controller: WelcomePlayback | null;
  onError: () => void;
  onBuffer: () => void;
  onReady: () => void;
}
