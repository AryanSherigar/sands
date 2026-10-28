import { BlurFilter, Container, Graphics } from "pixi.js";
import {
  LOCK_CENTER_X,
  LOCK_CENTER_Y,
  PICK_NEEDLE_LENGTH,
} from "../lockpickPresets";

const NEEDLE_BASE_COLOR = 0xdde7f0;
const NEEDLE_GLOW_COLOR = 0x7ec8ff;
const NEEDLE_TIP_COLOR = 0xffe680;

export interface NeedleScene {
  container: Container;
  updateAngle: (angleDeg: number, isVibrating: boolean) => void;
  playBreakAnim: () => void;
}

export function createNeedleScene(): NeedleScene {
  const container = new Container();

  const glowGraphics = new Graphics();
  glowGraphics.filters = [new BlurFilter({ strength: 4, quality: 3 })];
  container.addChild(glowGraphics);

  const needleGraphics = new Graphics();
  container.addChild(needleGraphics);

  const updateAngle = (angleDeg: number, isVibrating: boolean): void => {
    needleGraphics.clear();
    glowGraphics.clear();

    const jitter = isVibrating ? (Math.random() - 0.5) * 1.5 : 0;
    const rad = ((angleDeg + jitter) * Math.PI) / 180;
    const endX = LOCK_CENTER_X + Math.cos(rad) * PICK_NEEDLE_LENGTH;
    const endY = LOCK_CENTER_Y + Math.sin(rad) * PICK_NEEDLE_LENGTH;

    // Outer glow
    glowGraphics
      .moveTo(LOCK_CENTER_X, LOCK_CENTER_Y)
      .lineTo(endX, endY)
      .stroke({ color: NEEDLE_GLOW_COLOR, width: 6, alpha: 0.45, cap: "round" });

    // Sharp metallic needle
    needleGraphics
      .moveTo(LOCK_CENTER_X, LOCK_CENTER_Y)
      .lineTo(endX, endY)
      .stroke({ color: NEEDLE_BASE_COLOR, width: 2.5, alpha: 0.95, cap: "round" });

    // Glowing tip indicator
    needleGraphics
      .circle(endX, endY, 3.5)
      .fill({ color: NEEDLE_TIP_COLOR, alpha: 0.95 });
  };

  const playBreakAnim = (): void => {
    needleGraphics.clear();
    glowGraphics.clear();
    // Brief blank then redraws next frame
  };

  return {
    container,
    updateAngle,
    playBreakAnim,
  };
}
