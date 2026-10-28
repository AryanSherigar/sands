import type { ActiveSituation, SituationInterventionLever } from "../../../types/situation.types";

export interface StrategySituationsDrawerProps {
  isOpen: boolean;
  situations: ActiveSituation[];
  activeSituationId?: string | null;
  ordersRemaining: number;
  onClose: () => void;
  onCenterMap: (regionId: string) => void;
  onExecuteLever: (lever: SituationInterventionLever) => void;
  onCancelLever: (commandId: string) => void;
  onReviewEvent: (eventId: string) => void;
}
