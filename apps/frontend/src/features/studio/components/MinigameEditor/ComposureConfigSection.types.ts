import type { ComposureConfigShape } from "../../types/minigame.types";

export interface ComposureConfigSectionProps {
  config: ComposureConfigShape;
  onChange: (config: ComposureConfigShape) => void;
}
