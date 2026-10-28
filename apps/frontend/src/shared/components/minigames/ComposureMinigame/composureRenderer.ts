import { KEY_ARROW_GLYPHS } from "./composureControls";
import type { ComposureView } from "./composureEngine";
import { CANVAS_SIZE_PX, type ComposurePalette } from "./composurePresets";

const TARGET_RADIUS = CANVAS_SIZE_PX * 0.2;
const START_RADIUS = CANVAS_SIZE_PX * 0.46;
const RING_WIDTH = 3;
const PULSE_WIDTH = 5;
const KEY_FONT = `700 ${Math.round(CANVAS_SIZE_PX * 0.14)}px "IBM Plex Mono", monospace`;
const FULL_TURN = Math.PI * 2;
const TOP_ANGLE = -Math.PI / 2;

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

function beatProgress(view: ComposureView): number {
  if (view.nextBeat === null) return 0;
  return clamp01(1 - (view.nextBeat.timeMs - view.nowMs) / view.intervalMs);
}

function strokeCircle(
  context: CanvasRenderingContext2D,
  radius: number,
  color: string,
  width: number,
): void {
  context.beginPath();
  context.arc(CANVAS_SIZE_PX / 2, CANVAS_SIZE_PX / 2, radius, 0, FULL_TURN);
  context.strokeStyle = color;
  context.lineWidth = width;
  context.stroke();
}

function drawPulse(
  context: CanvasRenderingContext2D,
  progress: number,
  palette: ComposurePalette,
  isReduced: boolean,
): void {
  if (!isReduced) {
    const radius = START_RADIUS - (START_RADIUS - TARGET_RADIUS) * progress;
    strokeCircle(context, radius, palette.pulse, PULSE_WIDTH);
    return;
  }
  context.beginPath();
  context.arc(
    CANVAS_SIZE_PX / 2,
    CANVAS_SIZE_PX / 2,
    TARGET_RADIUS,
    TOP_ANGLE,
    TOP_ANGLE + FULL_TURN * progress,
  );
  context.strokeStyle = palette.pulse;
  context.lineWidth = PULSE_WIDTH;
  context.stroke();
}

function drawKey(
  context: CanvasRenderingContext2D,
  view: ComposureView,
  palette: ComposurePalette,
): void {
  if (view.nextBeat === null) return;
  const key = view.nextBeat.expectedKey;
  context.fillStyle = palette.key;
  context.font = KEY_FONT;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(`${key} ${KEY_ARROW_GLYPHS[key]}`, CANVAS_SIZE_PX / 2, CANVAS_SIZE_PX / 2);
}

// A static ring that fills replaces the contracting pulse under reduced effects.
export function drawComposureFrame(
  context: CanvasRenderingContext2D,
  view: ComposureView,
  palette: ComposurePalette,
  isReduced: boolean,
): void {
  context.fillStyle = palette.background;
  context.fillRect(0, 0, CANVAS_SIZE_PX, CANVAS_SIZE_PX);
  strokeCircle(context, TARGET_RADIUS, palette.ring, RING_WIDTH);
  drawPulse(context, beatProgress(view), palette, isReduced);
  drawKey(context, view, palette);
}
