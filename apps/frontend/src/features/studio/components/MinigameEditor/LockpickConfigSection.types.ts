import type { LockpickConfigShape } from "../../types/minigame.types";

export interface LockpickConfigSectionProps {
  config: LockpickConfigShape;
  onChange: (updated: LockpickConfigShape) => void;
}
