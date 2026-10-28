import {
  ComposureConfigShape,
  DodgeConfigShape,
  LockpickConfigShape,
  MinigameType,
} from "../../types/minigame.types";

export interface MinigamePreviewOverlayProps {
  minigameType: MinigameType;
  dodgeConfig: DodgeConfigShape;
  lockpickConfig: LockpickConfigShape;
  composureConfig: ComposureConfigShape;
  onClose: () => void;
}
