export interface SetUpLaterDialogProps {
  isOpen: boolean;
  isSaving: boolean;
  errorMessage: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}
