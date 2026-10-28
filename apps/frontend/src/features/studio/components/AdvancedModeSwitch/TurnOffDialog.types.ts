export interface TurnOffDialogProps {
  isOpen: boolean;
  isBusy: boolean;
  missingPublishItems?: readonly string[];
  onConfirm: () => void;
  onCancel: () => void;
}
