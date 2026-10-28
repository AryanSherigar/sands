import type { TermsCard } from "../../../types/scene.types";

export interface SceneTermsCardProps {
  card: TermsCard;
  counterpartName: string;
  currentTurn: number;
  isBusy: boolean;
  onConfirm: () => void;
  onDecline?: () => void;
}
