import type { Arc, LabelMap, Point } from "@/shared/types/strategy-map.types";

interface OrientedArc {
  start: number;
  points: Point[];
  isClosed: boolean;
}

const VERTEX_STRIDE = 100000;

function vertexKey(point: Point): number {
  return point.y * VERTEX_STRIDE + point.x;
}

function orientedArcsFor(label: number, arcs: Arc[]): OrientedArc[] {
  const result: OrientedArc[] = [];
  for (const arc of arcs) {
    if (arc.right !== label && arc.left !== label) continue;
    const points = arc.right === label ? arc.points : reversedPoints(arc);
    result.push({ start: vertexKey(points[0]), points, isClosed: arc.isClosed });
  }
  return result;
}

function reversedPoints(arc: Arc): Point[] {
  if (arc.isClosed) return [arc.points[0], ...arc.points.slice(1).reverse()];
  return [...arc.points].reverse();
}

function endKey(arc: OrientedArc): number {
  return vertexKey(arc.points[arc.points.length - 1]);
}

function chainRing(first: OrientedArc, byStart: Map<number, OrientedArc[]>): Point[] {
  const ring = [...first.points];
  let current = first;
  while (endKey(current) !== first.start) {
    const next = (byStart.get(endKey(current)) ?? []).shift();
    if (!next) break;
    ring.push(...next.points.slice(1));
    current = next;
  }
  if (ring.length > 1 && vertexKey(ring[ring.length - 1]) === first.start) ring.pop();
  return ring;
}

function buildRings(arcs: OrientedArc[]): Point[][] {
  const byStart = new Map<number, OrientedArc[]>();
  for (const arc of arcs.filter((item) => !item.isClosed)) {
    byStart.set(arc.start, [...(byStart.get(arc.start) ?? []), arc]);
  }
  const rings = arcs.filter((arc) => arc.isClosed).map((arc) => arc.points);
  for (const arc of arcs.filter((item) => !item.isClosed)) {
    const list = byStart.get(arc.start) ?? [];
    const index = list.indexOf(arc);
    if (index < 0) continue;
    list.splice(index, 1);
    rings.push(chainRing(arc, byStart));
  }
  return rings;
}

function isCollinear(before: Point, point: Point, after: Point): boolean {
  const cross = (point.x - before.x) * (after.y - point.y) - (point.y - before.y) * (after.x - point.x);
  const dot = (point.x - before.x) * (after.x - point.x) + (point.y - before.y) * (after.y - point.y);
  return cross === 0 && dot > 0;
}

function dropCollinear(ring: Point[]): Point[] {
  return ring.filter((point, index) => {
    const before = ring[(index + ring.length - 1) % ring.length];
    const after = ring[(index + 1) % ring.length];
    return !isCollinear(before, point, after);
  });
}

function rotateToTopLeft(ring: Point[]): Point[] {
  let best = 0;
  ring.forEach((point, index) => {
    const top = ring[best];
    if (point.y < top.y || (point.y === top.y && point.x < top.x)) best = index;
  });
  return [...ring.slice(best), ...ring.slice(0, best)];
}

function ringToPath(ring: Point[]): string {
  const [first, ...rest] = ring;
  const lines = rest.map((point) => `L${point.x} ${point.y}`);
  return [`M${first.x} ${first.y}`, ...lines, "Z"].join(" ");
}

export function assembleOutline(regionLabel: number, arcs: Arc[]): string {
  return buildRings(orientedArcsFor(regionLabel, arcs))
    .map((ring) => rotateToTopLeft(dropCollinear(ring)))
    .filter((ring) => ring.length >= 3)
    .sort((first, second) => first[0].y - second[0].y || first[0].x - second[0].x)
    .map(ringToPath)
    .join(" ");
}

function regionBounds(map: LabelMap, label: number): { x0: number; y0: number; x1: number; y1: number } {
  const bounds = { x0: map.width, y0: map.height, x1: -1, y1: -1 };
  for (let index = 0; index < map.labels.length; index++) {
    if (map.labels[index] !== label) continue;
    const x = index % map.width;
    const y = Math.floor(index / map.width);
    bounds.x0 = Math.min(bounds.x0, x);
    bounds.x1 = Math.max(bounds.x1, x);
    bounds.y0 = Math.min(bounds.y0, y);
    bounds.y1 = Math.max(bounds.y1, y);
  }
  return bounds;
}

function distanceGrid(map: LabelMap, label: number, bounds: ReturnType<typeof regionBounds>): number[][] {
  const rows = bounds.y1 - bounds.y0 + 1;
  const columns = bounds.x1 - bounds.x0 + 1;
  const far = rows + columns;
  const grid = Array.from({ length: rows }, (_, y) =>
    Array.from({ length: columns }, (_, x) =>
      map.labels[(y + bounds.y0) * map.width + x + bounds.x0] === label ? far : 0,
    ),
  );
  relaxGrid(grid);
  return grid;
}

function relaxGrid(grid: number[][]): void {
  const rows = grid.length;
  const columns = grid[0].length;
  const at = (y: number, x: number): number => (y < 0 || x < 0 || y >= rows || x >= columns ? 0 : grid[y][x]);
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < columns; x++) {
      if (grid[y][x] > 0) grid[y][x] = Math.min(grid[y][x], at(y - 1, x) + 1, at(y, x - 1) + 1);
    }
  }
  for (let y = rows - 1; y >= 0; y--) {
    for (let x = columns - 1; x >= 0; x--) {
      if (grid[y][x] > 0) grid[y][x] = Math.min(grid[y][x], at(y + 1, x) + 1, at(y, x + 1) + 1);
    }
  }
}

export function computeLabelPoint(map: LabelMap, label: number): Point {
  const bounds = regionBounds(map, label);
  const grid = distanceGrid(map, label, bounds);
  let best = { x: bounds.x0, y: bounds.y0, distance: -1 };
  grid.forEach((row, y) =>
    row.forEach((distance, x) => {
      if (distance > best.distance) best = { x: x + bounds.x0, y: y + bounds.y0, distance };
    }),
  );
  return { x: best.x, y: best.y };
}
