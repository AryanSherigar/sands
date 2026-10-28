export interface SceneComposerProps {
  isDisabled: boolean;
  exchangesRemaining: number;
  onSend: (text: string) => void;
}
