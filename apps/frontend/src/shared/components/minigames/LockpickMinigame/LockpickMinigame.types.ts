import type {
  LockpickConfigShape,
  MinigameOutcomeResult,
} from "@/shared/types/minigame.types";

export interface LockpickMinigameProps {
  lockpickConfig: LockpickConfigShape;
  onComplete: (result: MinigameOutcomeResult) => void;
}
