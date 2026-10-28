import type { PixelImage, Point } from "@/shared/types/strategy-map.types";
import { colorDistance, type Rgb } from "./clusterColors";
import { neighbourIndexes } from "./connectedComponents";
import { crossingsAt } from "./rasterizeOutlines";

const EDGE_EPSILON = 1e-6;
const RED_WEIGHT = 0.299;
const GREEN_WEIGHT = 0.587;
const BLUE_WEIGHT = 0.114;

function colorAt(picture: PixelImage, index: number): Rgb {
  const offset = index * 4;
  return [picture.data[offset], picture.data[offset + 1], picture.data[offset + 2]];
}

export function floodSelect(
  picture: PixelImage,
  start: Point,
  tolerance: number,
): Uint8Array {
  const mask = new Uint8Array(picture.width * picture.height);
  const first = start.y * picture.width + start.x;
  const target = colorAt(picture, first);
  const stack = [first];
  mask[first] = 1;
  while (stack.length > 0) {
    const index = stack.pop() as number;
    for (const next of neighbourIndexes(index, picture.width, picture.height)) {
      if (mask[next] === 1) continue;
      if (colorDistance(colorAt(picture, next), target) > tolerance) continue;
      mask[next] = 1;
      stack.push(next);
    }
  }
  return mask;
}

function grayscale(picture: PixelImage): Float32Array {
  const gray = new Float32Array(picture.width * picture.height);
  for (let index = 0; index < gray.length; index++) {
    const [red, green, blue] = colorAt(picture, index);
    gray[index] = RED_WEIGHT * red + GREEN_WEIGHT * green + BLUE_WEIGHT * blue;
  }
  return gray;
}

function sobelAt(gray: Float32Array, size: { width: number; height: number }, x: number, y: number): number {
  const at = (dx: number, dy: number): number => {
    const column = Math.min(size.width - 1, Math.max(0, x + dx));
    const row = Math.min(size.height - 1, Math.max(0, y + dy));
    return gray[row * size.width + column];
  };
  const gradientX = at(1, -1) + 2 * at(1, 0) + at(1, 1) - at(-1, -1) - 2 * at(-1, 0) - at(-1, 1);
  const gradientY = at(-1, 1) + 2 * at(0, 1) + at(1, 1) - at(-1, -1) - 2 * at(0, -1) - at(1, -1);
  return Math.hypot(gradientX, gradientY);
}

export function edgeStrength(picture: PixelImage): Float32Array {
  const gray = grayscale(picture);
  const strength = new Float32Array(gray.length);
  for (let y = 0; y < picture.height; y++) {
    for (let x = 0; x < picture.width; x++) {
      strength[y * picture.width + x] = sobelAt(gray, picture, x, y);
    }
  }
  return strength;
}

export function snapToEdge(
  strength: Float32Array,
  width: number,
  point: Point,
  radius: number,
): Point {
  const height = strength.length / width;
  let best = { x: point.x, y: point.y, value: EDGE_EPSILON, distance: 0 };
  for (let y = Math.max(0, point.y - radius); y <= Math.min(height - 1, point.y + radius); y++) {
    for (let x = Math.max(0, point.x - radius); x <= Math.min(width - 1, point.x + radius); x++) {
      const value = strength[y * width + x];
      const distance = Math.hypot(x - point.x, y - point.y);
      const isBetter = value > best.value || (value === best.value && distance < best.distance);
      if (value > EDGE_EPSILON && isBetter) best = { x, y, value, distance };
    }
  }
  return { x: best.x, y: best.y };
}

export function polygonMask(width: number, height: number, points: Point[]): Uint8Array {
  const mask = new Uint8Array(width * height);
  for (let y = 0; y < height; y++) {
    const crossings = crossingsAt([points], y + 0.5);
    for (let pair = 0; pair + 1 < crossings.length; pair += 2) {
      const from = Math.max(0, Math.ceil(crossings[pair] - 0.5));
      const to = Math.min(width, Math.ceil(crossings[pair + 1] - 0.5));
      for (let x = from; x < to; x++) mask[y * width + x] = 1;
    }
  }
  return mask;
}
