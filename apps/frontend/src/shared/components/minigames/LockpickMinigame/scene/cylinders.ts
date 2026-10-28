import { BlurFilter, Container, Graphics } from "pixi.js";
import { LOCK_CENTER_X, LOCK_CENTER_Y } from "../lockpickPresets";

const CYLINDER_UNCLICKED_COLOR = 0x1f2937;
const CYLINDER_BORDER_COLOR = 0x475569;
const CYLINDER_CLICKED_COLOR = 0xffbf36;
const CYLINDER_GLOW_COLOR = 0xffd152;

export interface CylindersScene {
  container: Container;
  updateCylinders: (clickedCount: number, totalCount: number) => void;
}

export function createCylindersScene(): CylindersScene {
  const container = new Container();

  const glowGraphics = new Graphics();
  glowGraphics.filters = [new BlurFilter({ strength: 4, quality: 3 })];
  container.addChild(glowGraphics);

  const cylinderGraphics = new Graphics();
  container.addChild(cylinderGraphics);

  const updateCylinders = (clickedCount: number, totalCount: number): void => {
    cylinderGraphics.clear();
    glowGraphics.clear();

    if (totalCount <= 0) return;

    // Distribute cylinder tumbler pins horizontally beneath the keyhole
    const slotWidth = 24;
    const slotHeight = 8;
    const gap = 8;
    const totalWidth = totalCount * slotWidth + (totalCount - 1) * gap;
    const startX = LOCK_CENTER_X - totalWidth / 2;
    const y = LOCK_CENTER_Y + 70;

    for (let i = 0; i < totalCount; i++) {
      const x = startX + i * (slotWidth + gap);
      const isEngaged = i < clickedCount;

      if (isEngaged) {
        // Glow
        glowGraphics
          .roundRect(x - 2, y - 2, slotWidth + 4, slotHeight + 4, 3)
          .fill({ color: CYLINDER_GLOW_COLOR, alpha: 0.55 });

        // Engaged pin
        cylinderGraphics
          .roundRect(x, y, slotWidth, slotHeight, 2)
          .fill(CYLINDER_CLICKED_COLOR);
      } else {
        // Unengaged pin slot
        cylinderGraphics
          .roundRect(x, y, slotWidth, slotHeight, 2)
          .fill(CYLINDER_UNCLICKED_COLOR);
        cylinderGraphics
          .roundRect(x, y, slotWidth, slotHeight, 2)
          .stroke({ color: CYLINDER_BORDER_COLOR, width: 1 });
      }
    }
  };

  return {
    container,
    updateCylinders,
  };
}
