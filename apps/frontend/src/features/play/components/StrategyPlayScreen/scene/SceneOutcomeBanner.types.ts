import type { SceneOutcome } from "../../../types/scene.types";

export interface SceneOutcomeBannerProps {
  outcome: SceneOutcome | null | undefined;
  onClose: () => void;
}
