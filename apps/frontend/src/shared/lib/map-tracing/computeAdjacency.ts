import { MIN_SHARED_BORDER } from "@/shared/constants/mapTracing";
import type { Arc } from "@/shared/types/strategy-map.types";

const PAIR_STRIDE = 65536;

function arcLength(arc: Arc): number {
  return arc.isClosed ? arc.points.length : arc.points.length - 1;
}

function sharedBorderLengths(arcs: Arc[]): Map<number, number> {
  const lengths = new Map<number, number>();
  for (const arc of arcs) {
    if (arc.left === 0 || arc.right === 0) continue;
    const key = Math.min(arc.left, arc.right) * PAIR_STRIDE + Math.max(arc.left, arc.right);
    lengths.set(key, (lengths.get(key) ?? 0) + arcLength(arc));
  }
  return lengths;
}

/** Call with unsimplified arcs: border length is counted in pixel edges. */
export function computeAdjacency(arcs: Arc[]): Map<number, Set<number>> {
  const adjacency = new Map<number, Set<number>>();
  const link = (from: number, to: number): void => {
    adjacency.set(from, (adjacency.get(from) ?? new Set<number>()).add(to));
  };
  for (const [key, length] of sharedBorderLengths(arcs)) {
    if (length < MIN_SHARED_BORDER) continue;
    const low = Math.floor(key / PAIR_STRIDE);
    const high = key % PAIR_STRIDE;
    link(low, high);
    link(high, low);
  }
  return adjacency;
}
