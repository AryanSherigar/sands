export interface ReadingStepProps {
  onFinish: () => void;
  onBack: () => void;
  onSkip: () => void;
  isSaving: boolean;
  errorMessage: string | null;
}
