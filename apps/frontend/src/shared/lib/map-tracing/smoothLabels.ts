import { SMOOTH_RADIUS } from "@/shared/constants/mapTracing";

function isBoundaryPixel(
  labels: Uint16Array,
  index: number,
  size: { width: number; height: number },
): boolean {
  const x = index % size.width;
  const y = Math.floor(index / size.width);
  const label = labels[index];
  return (
    (x > 0 && labels[index - 1] !== label) ||
    (x < size.width - 1 && labels[index + 1] !== label) ||
    (y > 0 && labels[index - size.width] !== label) ||
    (y < size.height - 1 && labels[index + size.width] !== label)
  );
}

function windowCounts(
  labels: Uint16Array,
  index: number,
  size: { width: number; height: number },
  counts: Map<number, number>,
): void {
  counts.clear();
  const x = index % size.width;
  const y = Math.floor(index / size.width);
  for (let row = Math.max(0, y - SMOOTH_RADIUS); row <= Math.min(size.height - 1, y + SMOOTH_RADIUS); row++) {
    for (let column = Math.max(0, x - SMOOTH_RADIUS); column <= Math.min(size.width - 1, x + SMOOTH_RADIUS); column++) {
      const label = labels[row * size.width + column];
      if (label !== 0) counts.set(label, (counts.get(label) ?? 0) + 1);
    }
  }
}

function winnerOf(counts: Map<number, number>, current: number): number {
  let best = current;
  let bestCount = counts.get(current) ?? 0;
  for (const [label, count] of counts) {
    if (count > bestCount || (count === bestCount && label < best && best !== current)) {
      best = label;
      bestCount = count;
    }
  }
  return best;
}

/** Majority filter on boundary pixels: erases stripes thinner than the window. */
export function smoothLabels(labels: Uint16Array, width: number, height: number): Uint16Array {
  const result = new Uint16Array(labels);
  const size = { width, height };
  const counts = new Map<number, number>();
  for (let index = 0; index < labels.length; index++) {
    if (labels[index] === 0 || !isBoundaryPixel(labels, index, size)) continue;
    windowCounts(labels, index, size, counts);
    result[index] = winnerOf(counts, labels[index]);
  }
  return result;
}
