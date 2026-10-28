export interface SaveStatusIndicatorProps {
  isSaving: boolean;
  lastSaved: Date | null;
  hasError?: boolean;
  onRetry?: () => void;
}
