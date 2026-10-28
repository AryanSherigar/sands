import type { Arc, Point } from "@/shared/types/strategy-map.types";

const MIN_RING_POINTS = 3;

function distanceToSegment(point: Point, start: Point, end: Point): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(point.x - start.x, point.y - start.y);
  const ratio = Math.max(
    0,
    Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared),
  );
  return Math.hypot(point.x - (start.x + ratio * dx), point.y - (start.y + ratio * dy));
}

function farthestPoint(
  points: Point[],
  range: { first: number; last: number },
): { index: number; distance: number } {
  let best = { index: range.first, distance: -1 };
  for (let index = range.first + 1; index < range.last; index++) {
    const distance = distanceToSegment(points[index], points[range.first], points[range.last]);
    if (distance > best.distance) best = { index, distance };
  }
  return best;
}

function simplifyOpen(points: Point[], tolerance: number): Point[] {
  if (tolerance <= 0 || points.length < MIN_RING_POINTS) return points;
  const isKept = new Array<boolean>(points.length).fill(false);
  isKept[0] = true;
  isKept[points.length - 1] = true;
  const stack = [{ first: 0, last: points.length - 1 }];
  while (stack.length > 0) {
    const range = stack.pop() as { first: number; last: number };
    const far = farthestPoint(points, range);
    if (far.distance <= tolerance) continue;
    isKept[far.index] = true;
    stack.push({ first: range.first, last: far.index }, { first: far.index, last: range.last });
  }
  return points.filter((_, index) => isKept[index]);
}

function farthestFromFirst(points: Point[]): number {
  let bestIndex = 0;
  let bestDistance = -1;
  points.forEach((point, index) => {
    const distance = Math.hypot(point.x - points[0].x, point.y - points[0].y);
    if (distance > bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
}

function simplifyRing(points: Point[], tolerance: number): Point[] {
  if (tolerance <= 0 || points.length <= MIN_RING_POINTS) return points;
  const far = farthestFromFirst(points);
  const firstHalf = simplifyOpen(points.slice(0, far + 1), tolerance);
  const secondHalf = simplifyOpen([...points.slice(far), points[0]], tolerance);
  const ring = [...firstHalf, ...secondHalf.slice(1, -1)];
  return ring.length >= MIN_RING_POINTS ? ring : points;
}

export function simplifyPolyline(
  points: Point[],
  tolerance: number,
  isClosed: boolean,
): Point[] {
  return isClosed ? simplifyRing(points, tolerance) : simplifyOpen(points, tolerance);
}

export function simplifyArcs(
  arcs: Arc[],
  toleranceByArc: Map<number, number>,
): Arc[] {
  return arcs.map((arc) => ({
    ...arc,
    points: simplifyPolyline(arc.points, toleranceByArc.get(arc.id) ?? 0, arc.isClosed),
  }));
}
