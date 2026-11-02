import type { TermsCard, TreatyVerdict } from "../../../../types/scene.types";

export interface NegotiationTreatyDrawerProps {
  isOpen: boolean;
  proposal: TermsCard | null;
  currentTurn: number;
  counterpartName: string;
  isBusy?: boolean;
  verdict?: TreatyVerdict | null;
  onClose: () => void;
  onSign: () => void;
  onDecline?: () => void;
}
