import type { ActiveSituation } from "../../../types/situation.types";

export interface StrategySituationBannerProps {
  situation: ActiveSituation;
  onCenterMap: (regionId: string) => void;
  onReviewEvent: (eventId: string) => void;
  onDismiss: () => void;
}
