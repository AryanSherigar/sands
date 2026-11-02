export interface NegotiationConsoleProps {
  isDisabled?: boolean;
  hasPendingProposal?: boolean;
  isDrawerOpen?: boolean;
  isDeclinable?: boolean;
  onSend: (text: string) => void;
  onToggleDrawer: () => void;
  onBreakTalks: () => void;
}
