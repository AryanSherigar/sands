export interface StepFooterProps {
  onNext: () => void;
  nextLabel?: string;
  isNextDisabled?: boolean;
  isBusy?: boolean;
  onBack?: () => void;
  onSkip?: () => void;
}
