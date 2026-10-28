import { BlurFilter, Container, Graphics } from "pixi.js";
import {
  KEYHOLE_RADIUS,
  LOCK_CANVAS_HEIGHT,
  LOCK_CANVAS_WIDTH,
  LOCK_CENTER_X,
  LOCK_CENTER_Y,
  LOCK_INNER_RADIUS,
  LOCK_OUTER_RADIUS,
} from "../lockpickPresets";

const LOCK_FACE_BG = 0x0a0c14;
const LOCK_RIM_COLOR = 0x2b3545;
const LOCK_CORE_COLOR = 0x05070a;
const SWEET_SPOT_COLOR = 0xffbf36;
const SWEET_SPOT_DWELL_COLOR = 0xffe680;
const TENSION_WARN_COLOR = 0xff4d4d;
const BREAK_FLASH_COLOR = 0xff2222;
const UNLOCK_FLASH_COLOR = 0x44ff88;

export interface LockScene {
  container: Container;
  updateSweetSpot: (
    centerDeg: number,
    arcDeg: number,
    dwellProgress: number,
    tensionProgress: number,
  ) => void;
  flashBreak: () => void;
  flashUnlock: () => void;
}

export function createLockScene(): LockScene {
  const container = new Container();

  // 1. Dark circular backdrop plate
  const background = new Graphics();
  background
    .circle(LOCK_CENTER_X, LOCK_CENTER_Y, LOCK_OUTER_RADIUS + 15)
    .fill(LOCK_FACE_BG);
  background
    .circle(LOCK_CENTER_X, LOCK_CENTER_Y, LOCK_OUTER_RADIUS + 15)
    .stroke({ color: LOCK_RIM_COLOR, width: 4 });
  background
    .circle(LOCK_CENTER_X, LOCK_CENTER_Y, LOCK_INNER_RADIUS)
    .fill(LOCK_CORE_COLOR);
  background
    .circle(LOCK_CENTER_X, LOCK_CENTER_Y, LOCK_INNER_RADIUS)
    .stroke({ color: 0x18202c, width: 2 });

  // Add decorative circular ticks around the lock face
  for (let angle = 0; angle < 360; angle += 15) {
    const rad = (angle * Math.PI) / 180;
    const isMajor = angle % 45 === 0;
    const rInner = isMajor ? LOCK_OUTER_RADIUS - 8 : LOCK_OUTER_RADIUS - 4;
    const rOuter = LOCK_OUTER_RADIUS + 8;
    const x1 = LOCK_CENTER_X + Math.cos(rad) * rInner;
    const y1 = LOCK_CENTER_Y + Math.sin(rad) * rInner;
    const x2 = LOCK_CENTER_X + Math.cos(rad) * rOuter;
    const y2 = LOCK_CENTER_Y + Math.sin(rad) * rOuter;
    background
      .moveTo(x1, y1)
      .lineTo(x2, y2)
      .stroke({ color: isMajor ? 0x4b596e : 0x222a36, width: isMajor ? 2 : 1 });
  }

  // Keyhole shape at center
  background.circle(LOCK_CENTER_X, LOCK_CENTER_Y, KEYHOLE_RADIUS).fill(0x020305);
  background
    .poly([
      { x: LOCK_CENTER_X - 10, y: LOCK_CENTER_Y },
      { x: LOCK_CENTER_X + 10, y: LOCK_CENTER_Y },
      { x: LOCK_CENTER_X + 16, y: LOCK_CENTER_Y + 45 },
      { x: LOCK_CENTER_X - 16, y: LOCK_CENTER_Y + 45 },
    ])
    .fill(0x020305);

  container.addChild(background);

  // 2. Sweet-spot arc graphics
  const sweetSpotGlow = new Graphics();
  sweetSpotGlow.filters = [new BlurFilter({ strength: 5, quality: 3 })];
  container.addChild(sweetSpotGlow);

  const sweetSpotArc = new Graphics();
  container.addChild(sweetSpotArc);

  // 3. Tension warning ring (subtle ring around sweet-spot when outside)
  const tensionRing = new Graphics();
  container.addChild(tensionRing);

  // 4. Flash overlay
  const flashOverlay = new Graphics();
  container.addChild(flashOverlay);

  const updateSweetSpot = (
    centerDeg: number,
    arcDeg: number,
    dwellProgress: number,
    tensionProgress: number,
  ): void => {
    sweetSpotArc.clear();
    sweetSpotGlow.clear();
    tensionRing.clear();

    const startRad = ((centerDeg - arcDeg / 2) * Math.PI) / 180;
    const endRad = ((centerDeg + arcDeg / 2) * Math.PI) / 180;
    const midR = (LOCK_OUTER_RADIUS + LOCK_INNER_RADIUS) / 2;
    const strokeWidth = LOCK_OUTER_RADIUS - LOCK_INNER_RADIUS - 4;

    // Glowing arc
    sweetSpotGlow
      .arc(LOCK_CENTER_X, LOCK_CENTER_Y, midR, startRad, endRad)
      .stroke({
        color: SWEET_SPOT_COLOR,
        width: strokeWidth + 6,
        alpha: 0.6,
        cap: "round",
      });

    // Solid arc
    sweetSpotArc
      .arc(LOCK_CENTER_X, LOCK_CENTER_Y, midR, startRad, endRad)
      .stroke({
        color: dwellProgress > 0 ? SWEET_SPOT_DWELL_COLOR : SWEET_SPOT_COLOR,
        width: strokeWidth,
        alpha: 0.9,
        cap: "round",
      });

    // Dwell progress fill line along center of arc
    if (dwellProgress > 0) {
      const dwellEndRad = startRad + (endRad - startRad) * dwellProgress;
      sweetSpotArc
        .arc(LOCK_CENTER_X, LOCK_CENTER_Y, midR, startRad, dwellEndRad)
        .stroke({
          color: 0xffffff,
          width: 4,
          alpha: 0.95,
          cap: "round",
        });
    }

    // Tension warning line along outer rim if building tension
    if (tensionProgress > 0.2) {
      const tensionAlpha = Math.min(1, tensionProgress);
      tensionRing
        .circle(LOCK_CENTER_X, LOCK_CENTER_Y, LOCK_OUTER_RADIUS + 12)
        .stroke({
          color: TENSION_WARN_COLOR,
          width: 3,
          alpha: tensionAlpha * 0.7,
        });
    }
  };

  const flashBreak = (): void => {
    flashOverlay.clear();
    flashOverlay
      .rect(0, 0, LOCK_CANVAS_WIDTH, LOCK_CANVAS_HEIGHT)
      .fill({ color: BREAK_FLASH_COLOR, alpha: 0.35 });

    setTimeout(() => {
      flashOverlay.clear();
    }, 180);
  };

  const flashUnlock = (): void => {
    flashOverlay.clear();
    flashOverlay
      .rect(0, 0, LOCK_CANVAS_WIDTH, LOCK_CANVAS_HEIGHT)
      .fill({ color: UNLOCK_FLASH_COLOR, alpha: 0.4 });

    setTimeout(() => {
      flashOverlay.clear();
    }, 300);
  };

  return {
    container,
    updateSweetSpot,
    flashBreak,
    flashUnlock,
  };
}
