export interface NegotiationHeaderProps {
  title: string;
  exchangesRemaining: number;
  totalExchanges?: number;
  isFinished?: boolean;
  onExit: () => void;
  onToggleChronicles?: () => void;
}
