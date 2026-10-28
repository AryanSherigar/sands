import type {
  ComposureConfigShape,
  MinigameOutcomeResult,
} from "@/shared/types/minigame.types";

export interface ComposureMinigameProps {
  composureConfig: ComposureConfigShape;
  onComplete: (result: MinigameOutcomeResult) => void;
}
