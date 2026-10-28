import type { LabelMap, PixelImage } from "@/shared/types/strategy-map.types";

type Rgb = [number, number, number];

const OPAQUE_ALPHA = 255;
const CHANNEL_MAX = 255;
const LCG_MULTIPLIER = 1664525;
const LCG_INCREMENT = 1013904223;
const LCG_MODULUS = 2 ** 32;

export function makeBlockImage(
  rows: string[],
  palette: Record<string, Rgb>,
  cellSize: number,
): PixelImage {
  const width = rows[0].length * cellSize;
  const height = rows.length * cellSize;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const key = rows[Math.floor(y / cellSize)][Math.floor(x / cellSize)];
      const offset = (y * width + x) * 4;
      data.set([...palette[key], OPAQUE_ALPHA], offset);
    }
  }
  return { width, height, data };
}

export function addNoise(
  image: PixelImage,
  amplitude: number,
  seed: number,
): PixelImage {
  let state = seed >>> 0;
  const nextOffset = (): number => {
    state = (state * LCG_MULTIPLIER + LCG_INCREMENT) % LCG_MODULUS;
    return Math.floor((state / LCG_MODULUS) * (2 * amplitude + 1)) - amplitude;
  };
  const data = new Uint8ClampedArray(image.data);
  for (let index = 0; index < data.length; index++) {
    const isAlpha = index % 4 === 3;
    if (isAlpha) continue;
    data[index] = Math.min(CHANNEL_MAX, Math.max(0, data[index] + nextOffset()));
  }
  return { width: image.width, height: image.height, data };
}

const EMPTY_CELL = ".";
const TEST_ID_DIGITS = 2;

export function makeLabelMapFromRows(rows: string[]): LabelMap {
  const width = rows[0].length;
  const height = rows.length;
  const labels = new Uint16Array(width * height);
  const labelByChar = new Map<string, number>();
  rows.forEach((row, y) => {
    [...row].forEach((char, x) => {
      if (char === EMPTY_CELL) return;
      if (!labelByChar.has(char)) labelByChar.set(char, labelByChar.size + 1);
      labels[y * width + x] = labelByChar.get(char) as number;
    });
  });
  const entries = [...labelByChar.values()].map((label) => ({
    label,
    id: `region_${String(label).padStart(TEST_ID_DIGITS, "0")}`,
    sourceColor: null,
  }));
  return { width, height, labels, entries, nextIdNumber: entries.length + 1 };
}
