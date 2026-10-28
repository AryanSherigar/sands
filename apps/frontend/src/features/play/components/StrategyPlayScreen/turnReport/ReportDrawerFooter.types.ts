export interface ReportDrawerFooterProps {
  autoShowTurnReport: boolean;
  onToggleAutoShow: (enabled: boolean) => void;
  onDismiss: () => void;
  onContinue?: () => void;
}
