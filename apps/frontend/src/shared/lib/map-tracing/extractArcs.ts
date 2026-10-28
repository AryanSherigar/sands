import type { Arc, LabelMap, Point } from "@/shared/types/strategy-map.types";

interface BoundaryEdge {
  from: number;
  to: number;
  /** Labels on either side: west/east for vertical edges, above/below for horizontal. */
  first: number;
  second: number;
  isHorizontal: boolean;
}

interface EdgeGraph {
  edges: BoundaryEdge[];
  incident: Map<number, number[]>;
  columns: number;
}

function labelAt(map: LabelMap, x: number, y: number): number {
  const isOutside = x < 0 || y < 0 || x >= map.width || y >= map.height;
  return isOutside ? 0 : map.labels[y * map.width + x];
}

function collectEdges(map: LabelMap): BoundaryEdge[] {
  const columns = map.width + 1;
  const edges: BoundaryEdge[] = [];
  for (let y = 0; y <= map.height; y++) {
    for (let x = 0; x <= map.width; x++) {
      const west = labelAt(map, x - 1, y);
      const east = labelAt(map, x, y);
      if (y < map.height && west !== east) {
        const from = y * columns + x;
        edges.push({ from, to: from + columns, first: west, second: east, isHorizontal: false });
      }
      const above = labelAt(map, x, y - 1);
      if (x < map.width && above !== east) {
        const from = y * columns + x;
        edges.push({ from, to: from + 1, first: above, second: east, isHorizontal: true });
      }
    }
  }
  return edges;
}

function buildGraph(map: LabelMap): EdgeGraph {
  const edges = collectEdges(map);
  const incident = new Map<number, number[]>();
  edges.forEach((edge, index) => {
    for (const vertex of [edge.from, edge.to]) {
      const list = incident.get(vertex) ?? [];
      list.push(index);
      incident.set(vertex, list);
    }
  });
  return { edges, incident, columns: map.width + 1 };
}

function pairKey(edge: BoundaryEdge): number {
  const low = Math.min(edge.first, edge.second);
  const high = Math.max(edge.first, edge.second);
  return low * 65536 + high;
}

function isJunction(graph: EdgeGraph, vertex: number): boolean {
  const list = graph.incident.get(vertex) ?? [];
  if (list.length !== 2) return true;
  return pairKey(graph.edges[list[0]]) !== pairKey(graph.edges[list[1]]);
}

function leftLabel(edge: BoundaryEdge, isForward: boolean): number {
  if (edge.isHorizontal) return isForward ? edge.first : edge.second;
  return isForward ? edge.second : edge.first;
}

function vertexPoint(graph: EdgeGraph, vertex: number): Point {
  return { x: vertex % graph.columns, y: Math.floor(vertex / graph.columns) };
}

function otherEnd(edge: BoundaryEdge, vertex: number): number {
  return edge.from === vertex ? edge.to : edge.from;
}

function walkArc(
  graph: EdgeGraph,
  visited: Set<number>,
  start: number,
  firstEdgeIndex: number,
  id: number,
): Arc {
  const first = graph.edges[firstEdgeIndex];
  const left = leftLabel(first, first.from === start);
  const right = left === first.first ? first.second : first.first;
  const points = [vertexPoint(graph, start)];
  let current = start;
  let edgeIndex = firstEdgeIndex;
  for (;;) {
    visited.add(edgeIndex);
    current = otherEnd(graph.edges[edgeIndex], current);
    points.push(vertexPoint(graph, current));
    if (current === start || isJunction(graph, current)) break;
    const list = graph.incident.get(current) as number[];
    edgeIndex = list[0] === edgeIndex ? list[1] : list[0];
  }
  const isClosed = current === start;
  if (isClosed) points.pop();
  return { id, left, right, points, isClosed };
}

function sortedJunctions(graph: EdgeGraph): number[] {
  return [...graph.incident.keys()]
    .filter((vertex) => isJunction(graph, vertex))
    .sort((first, second) => first - second);
}

export function extractArcs(map: LabelMap): Arc[] {
  const graph = buildGraph(map);
  const visited = new Set<number>();
  const arcs: Arc[] = [];
  const startFrom = (vertex: number): void => {
    for (const edgeIndex of graph.incident.get(vertex) ?? []) {
      if (visited.has(edgeIndex)) continue;
      arcs.push(walkArc(graph, visited, vertex, edgeIndex, arcs.length));
    }
  };
  sortedJunctions(graph).forEach(startFrom);
  graph.edges.forEach((edge, index) => {
    if (!visited.has(index)) startFrom(edge.from);
  });
  return arcs;
}
