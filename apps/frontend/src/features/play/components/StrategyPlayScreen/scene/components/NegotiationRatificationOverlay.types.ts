import type { SceneOutcome } from "../../../../types/scene.types";

export interface NegotiationRatificationOverlayProps {
  outcome?: SceneOutcome | null;
  counterpartName: string;
  onClose: () => void;
}
