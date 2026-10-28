import type { LabelEntry, LabelMap, Point } from "@/shared/types/strategy-map.types";
import { connectedComponents, neighbourIndexes } from "./connectedComponents";

const ID_DIGITS = 2;

function cloneMap(map: LabelMap): LabelMap {
  return {
    ...map,
    labels: new Uint16Array(map.labels),
    entries: map.entries.map((entry) => ({ ...entry })),
  };
}

function labelFor(map: LabelMap, id: string): number {
  const entry = map.entries.find((item) => item.id === id);
  if (!entry) throw new Error(`Unknown region id: ${id}`);
  return entry.label;
}

function nextLabel(map: LabelMap): number {
  return Math.max(0, ...map.entries.map((entry) => entry.label)) + 1;
}

function formatId(number: number): string {
  return `region_${String(number).padStart(ID_DIGITS, "0")}`;
}

function pruneEmpty(map: LabelMap): LabelMap {
  const used = new Set(map.labels);
  return { ...map, entries: map.entries.filter((entry) => used.has(entry.label)) };
}

function relabel(map: LabelMap, from: number, to: number): void {
  for (let index = 0; index < map.labels.length; index++) {
    if (map.labels[index] === from) map.labels[index] = to;
  }
}

export function mergeRegions(map: LabelMap, keepId: string, removeId: string): LabelMap {
  const result = cloneMap(map);
  const removeLabel = labelFor(result, removeId);
  relabel(result, removeLabel, labelFor(result, keepId));
  result.entries = result.entries.filter((entry) => entry.label !== removeLabel);
  return result;
}

export function deleteRegion(map: LabelMap, id: string): LabelMap {
  const result = cloneMap(map);
  const label = labelFor(result, id);
  relabel(result, label, 0);
  result.entries = result.entries.filter((entry) => entry.label !== label);
  return result;
}

export function paintMask(map: LabelMap, mask: Uint8Array, id: string): LabelMap {
  const result = cloneMap(map);
  const label = labelFor(result, id);
  mask.forEach((isMasked, index) => {
    if (isMasked !== 0) result.labels[index] = label;
  });
  return pruneEmpty(result);
}

export function paintBrush(map: LabelMap, center: Point, radius: number, id: string): LabelMap {
  const mask = new Uint8Array(map.labels.length);
  for (let y = Math.max(0, center.y - radius); y <= Math.min(map.height - 1, center.y + radius); y++) {
    for (let x = Math.max(0, center.x - radius); x <= Math.min(map.width - 1, center.x + radius); x++) {
      const isInside = (x - center.x) ** 2 + (y - center.y) ** 2 <= radius ** 2;
      if (isInside) mask[y * map.width + x] = 1;
    }
  }
  return paintMask(map, mask, id);
}

function addEntry(map: LabelMap, sourceColor: string | null): LabelEntry {
  const entry = { label: nextLabel(map), id: formatId(map.nextIdNumber), sourceColor };
  map.entries.push(entry);
  map.nextIdNumber += 1;
  return entry;
}

export function addRegion(
  map: LabelMap,
  mask: Uint8Array,
  sourceColor: string | null,
): { map: LabelMap; id: string } {
  const result = cloneMap(map);
  const entry = addEntry(result, sourceColor);
  mask.forEach((isMasked, index) => {
    if (isMasked !== 0) result.labels[index] = entry.label;
  });
  return { map: pruneEmpty(result), id: entry.id };
}

function segmentPoints(from: Point, to: Point): Point[] {
  const span = Math.max(Math.abs(to.x - from.x), Math.abs(to.y - from.y));
  if (span === 0) return [from];
  return Array.from({ length: span + 1 }, (_, step) => ({
    x: Math.round(from.x + ((to.x - from.x) * step) / span),
    y: Math.round(from.y + ((to.y - from.y) * step) / span),
  }));
}

function lineIndexes(map: LabelMap, line: Point[]): number[] {
  const points = line.length === 1 ? line : line.slice(1).flatMap((to, i) => segmentPoints(line[i], to));
  return points
    .filter((point) => point.x >= 0 && point.y >= 0 && point.x < map.width && point.y < map.height)
    .map((point) => point.y * map.width + point.x);
}

function absorbBarrier(map: LabelMap, barrier: number[], pieceLabels: Set<number>, fallback: number): void {
  let pending = barrier;
  while (pending.length > 0) {
    const stillPending: number[] = [];
    const assignments = new Map<number, number>();
    for (const index of pending) {
      const around = neighbourIndexes(index, map.width, map.height)
        .map((next) => map.labels[next])
        .filter((label) => pieceLabels.has(label));
      if (around.length > 0) assignments.set(index, Math.min(...around));
      else stillPending.push(index);
    }
    assignments.forEach((label, index) => (map.labels[index] = label));
    if (assignments.size === 0) {
      stillPending.forEach((index) => (map.labels[index] = fallback));
      return;
    }
    pending = stillPending;
  }
}

export function splitRegion(map: LabelMap, id: string, cutLine: Point[]): LabelMap {
  const result = cloneMap(map);
  const label = labelFor(result, id);
  const barrier = [...new Set(lineIndexes(result, cutLine))].filter((index) => result.labels[index] === label);
  barrier.forEach((index) => (result.labels[index] = 0));
  const { ids, sizes, labelOf } = connectedComponents(result.labels, result.width, result.height);
  const pieces = sizes
    .map((size, component) => ({ size, component }))
    .filter((piece) => labelOf[piece.component] === label)
    .sort((first, second) => second.size - first.size || first.component - second.component);
  const pieceLabels = new Set([label]);
  pieces.slice(1).forEach((piece) => {
    const entry = addEntry(result, result.entries.find((item) => item.label === label)?.sourceColor ?? null);
    pieceLabels.add(entry.label);
    ids.forEach((component, index) => {
      if (component === piece.component) result.labels[index] = entry.label;
    });
  });
  absorbBarrier(result, barrier, pieceLabels, label);
  return pruneEmpty(result);
}

export function downscaleLabelMap(map: LabelMap, factor: number): LabelMap {
  const width = Math.ceil(map.width / factor);
  const height = Math.ceil(map.height / factor);
  const labels = new Uint16Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      labels[y * width + x] = map.labels[y * factor * map.width + x * factor];
    }
  }
  return { ...map, width, height, labels, entries: map.entries.map((entry) => ({ ...entry })) };
}

export function createEmptyLabelMap(width: number, height: number): LabelMap {
  return { width, height, labels: new Uint16Array(width * height), entries: [], nextIdNumber: 1 };
}
