import {
  RECOMMENDED_MIN_REGIONS,
  TINY_REGION_PIXELS,
} from "@/shared/constants/mapTracing";
import type {
  MapDocument,
  MapProblem,
  MapProblemKind,
  RegionMeta,
} from "@/shared/types/strategy-map.types";

const WARNING_KINDS: ReadonlySet<MapProblemKind> = new Set([
  "tiny",
  "split_color",
  "few_regions",
]);

function metaProblems(
  document: MapDocument,
  meta: Record<string, RegionMeta>,
): MapProblem[] {
  const problems: MapProblem[] = [];
  for (const region of document.regions) {
    const entry = meta[region.id];
    if (!entry?.name.trim()) {
      problems.push({ regionId: region.id, kind: "unnamed", detail: "Give this region a name" });
    }
    if (!entry?.terrain) {
      problems.push({ regionId: region.id, kind: "no_terrain", detail: "Choose a terrain" });
    }
  }
  return problems;
}

function oneWayProblems(document: MapDocument): MapProblem[] {
  const neighbors = new Map(document.regions.map((region) => [region.id, new Set(region.neighbor_ids)]));
  const problems: MapProblem[] = [];
  for (const region of document.regions) {
    for (const neighborId of region.neighbor_ids) {
      if (neighbors.get(neighborId)?.has(region.id) === false) {
        problems.push({ regionId: region.id, kind: "one_way_link", detail: `Link to ${neighborId} is not mutual` });
      }
    }
  }
  return problems;
}

function undirectedAdjacency(document: MapDocument): Map<string, Set<string>> {
  const adjacency = new Map<string, Set<string>>(
    document.regions.map((region) => [region.id, new Set<string>()]),
  );
  for (const region of document.regions) {
    for (const neighborId of region.neighbor_ids) {
      if (!adjacency.has(neighborId)) continue;
      adjacency.get(region.id)?.add(neighborId);
      adjacency.get(neighborId)?.add(region.id);
    }
  }
  return adjacency;
}

function collectGroup(start: string, adjacency: Map<string, Set<string>>): string[] {
  const seen = new Set([start]);
  const stack = [start];
  while (stack.length > 0) {
    const current = stack.pop() as string;
    for (const next of adjacency.get(current) ?? []) {
      if (seen.has(next)) continue;
      seen.add(next);
      stack.push(next);
    }
  }
  return [...seen].sort();
}

function disconnectedProblems(document: MapDocument): MapProblem[] {
  const adjacency = undirectedAdjacency(document);
  const visited = new Set<string>();
  const groups: string[][] = [];
  for (const id of [...adjacency.keys()].sort()) {
    if (visited.has(id)) continue;
    const group = collectGroup(id, adjacency);
    group.forEach((member) => visited.add(member));
    groups.push(group);
  }
  groups.sort((first, second) => second.length - first.length);
  return groups.slice(1).map((group) => ({
    regionId: group[0],
    kind: "disconnected" as const,
    detail: "Not connected to the rest of the map",
  }));
}

function sizeProblems(
  document: MapDocument,
  pixelCounts: Record<string, number>,
): MapProblem[] {
  const problems: MapProblem[] = document.regions
    .filter((region) => (pixelCounts[region.id] ?? Infinity) < TINY_REGION_PIXELS)
    .map((region) => ({ regionId: region.id, kind: "tiny" as const, detail: "Very small region" }));
  if (document.regions.length < RECOMMENDED_MIN_REGIONS) {
    problems.push({
      regionId: null,
      kind: "few_regions",
      detail: `Fewer than ${RECOMMENDED_MIN_REGIONS} regions may feel small for long play`,
    });
  }
  return problems;
}

export function checkMap(
  document: MapDocument,
  meta: Record<string, RegionMeta>,
  pixelCounts: Record<string, number> = {},
): MapProblem[] {
  return [
    ...metaProblems(document, meta),
    ...oneWayProblems(document),
    ...disconnectedProblems(document),
    ...sizeProblems(document, pixelCounts),
  ];
}

export function isBlockingProblem(problem: MapProblem): boolean {
  return !WARNING_KINDS.has(problem.kind);
}

export function isMapFinishable(problems: MapProblem[]): boolean {
  return !problems.some(isBlockingProblem);
}
