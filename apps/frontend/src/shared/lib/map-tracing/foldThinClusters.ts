import { MIN_REGION_THICKNESS } from "@/shared/constants/mapTracing";
import { neighbourIndexes } from "./connectedComponents";

interface Size {
  width: number;
  height: number;
}

function distanceToEdge(labels: Uint16Array, size: Size): Int32Array {
  const distance = new Int32Array(labels.length);
  const at = (index: number, other: number, isInside: boolean): number =>
    isInside && labels[other] === labels[index] ? distance[other] : 0;
  for (let index = 0; index < labels.length; index++) {
    const x = index % size.width;
    const left = at(index, index - 1, x > 0);
    const up = at(index, index - size.width, index >= size.width);
    distance[index] = 1 + Math.min(left, up);
  }
  for (let index = labels.length - 1; index >= 0; index--) {
    const x = index % size.width;
    const right = at(index, index + 1, x < size.width - 1);
    const down = at(index, index + size.width, index + size.width < labels.length);
    distance[index] = Math.min(distance[index], 1 + Math.min(right, down));
  }
  return distance;
}

function thicknessByLabel(labels: Uint16Array, size: Size): Map<number, number> {
  const distance = distanceToEdge(labels, size);
  const thickness = new Map<number, number>();
  labels.forEach((label, index) => {
    if (label !== 0 && distance[index] > (thickness.get(label) ?? 0)) thickness.set(label, distance[index]);
  });
  return thickness;
}

function fillFromNeighbours(labels: Uint16Array, isErased: Uint8Array, size: Size): void {
  const queue: number[] = [];
  for (let index = 0; index < labels.length; index++) {
    if (isErased[index] === 1) continue;
    const touchesErased = neighbourIndexes(index, size.width, size.height).some((next) => isErased[next] === 1);
    if (touchesErased && labels[index] !== 0) queue.push(index);
  }
  for (let head = 0; head < queue.length; head++) {
    const index = queue[head];
    for (const next of neighbourIndexes(index, size.width, size.height)) {
      if (isErased[next] !== 1) continue;
      labels[next] = labels[index];
      isErased[next] = 0;
      queue.push(next);
    }
  }
}

/** Erases clusters too thin to be regions (edge blur) and returns folded label → pixel count. */
export function foldThinClusters(
  labels: Uint16Array,
  size: Size,
  protectedLabels: Set<number>,
): Map<number, number> {
  const thickness = thicknessByLabel(labels, size);
  const thin = new Set(
    [...thickness]
      .filter(([label, value]) => value < MIN_REGION_THICKNESS && !protectedLabels.has(label))
      .map(([label]) => label),
  );
  const folded = new Map<number, number>();
  if (thin.size === 0 || thin.size === thickness.size) return folded;
  const isErased = new Uint8Array(labels.length);
  labels.forEach((label, index) => {
    if (!thin.has(label)) return;
    isErased[index] = 1;
    folded.set(label, (folded.get(label) ?? 0) + 1);
  });
  fillFromNeighbours(labels, isErased, size);
  return folded;
}
