import {
  MAP_SCHEMA_VERSION,
  MAX_NAME_CHARS,
  MAX_OUTLINE_CHARS,
  MAX_REGIONS,
  MAX_SIMPLIFY_TOLERANCE,
  SIMPLIFY_GROWTH,
  START_SIMPLIFY_TOLERANCE,
} from "@/shared/constants/mapTracing";
import type {
  Arc,
  LabelEntry,
  LabelMap,
  MapDocument,
  MapProblem,
  MapRegion,
  RegionMeta,
  TraceOptions,
  TraceResult,
} from "@/shared/types/strategy-map.types";
import { assembleOutline, computeLabelPoint } from "./assembleRegions";
import { computeAdjacency } from "./computeAdjacency";
import { connectedComponents } from "./connectedComponents";
import { extractArcs } from "./extractArcs";
import { simplifyArcs } from "./simplifyArcs";

interface Simplified {
  arcs: Arc[];
  outlines: Map<number, string>;
  tooDetailed: Set<number>;
}

function countPixels(map: LabelMap): Map<number, number> {
  const counts = new Map<number, number>();
  map.labels.forEach((label) => counts.set(label, (counts.get(label) ?? 0) + 1));
  return counts;
}

function touchesAny(arc: Arc, labels: Set<number>): boolean {
  return labels.has(arc.left) || labels.has(arc.right);
}

function growTolerances(
  arcs: Arc[],
  grow: Set<number>,
  frozen: Set<number>,
  toleranceByArc: Map<number, number>,
): boolean {
  let hasGrown = false;
  for (const arc of arcs) {
    if (!touchesAny(arc, grow) || touchesAny(arc, frozen)) continue;
    const current = toleranceByArc.get(arc.id) as number;
    if (current >= MAX_SIMPLIFY_TOLERANCE) continue;
    toleranceByArc.set(arc.id, Math.min(MAX_SIMPLIFY_TOLERANCE, current * SIMPLIFY_GROWTH));
    hasGrown = true;
  }
  return hasGrown;
}

function revertTolerances(
  arcs: Arc[],
  collapsed: Set<number>,
  previous: Map<number, number>,
  toleranceByArc: Map<number, number>,
): void {
  for (const arc of arcs) {
    if (touchesAny(arc, collapsed)) toleranceByArc.set(arc.id, previous.get(arc.id) as number);
  }
}

function simplifyOnce(
  rawArcs: Arc[],
  labels: number[],
  toleranceByArc: Map<number, number>,
): { arcs: Arc[]; outlines: Map<number, string> } {
  const arcs = simplifyArcs(rawArcs, toleranceByArc);
  const outlines = new Map(labels.map((label) => [label, assembleOutline(label, arcs)]));
  return { arcs, outlines };
}

function simplifyUntilFits(
  rawArcs: Arc[],
  labels: number[],
  maxOutlineChars: number,
): Simplified {
  const toleranceByArc = new Map<number, number>(
    rawArcs.map((arc) => [arc.id, START_SIMPLIFY_TOLERANCE]),
  );
  const frozen = new Set<number>();
  let previous = new Map(toleranceByArc);
  for (;;) {
    const { arcs, outlines } = simplifyOnce(rawArcs, labels, toleranceByArc);
    const collapsed = new Set(labels.filter((label) => !frozen.has(label) && outlines.get(label) === ""));
    if (collapsed.size > 0) {
      revertTolerances(rawArcs, collapsed, previous, toleranceByArc);
      collapsed.forEach((label) => frozen.add(label));
      continue;
    }
    const oversized = new Set(labels.filter((label) => (outlines.get(label) as string).length > maxOutlineChars));
    previous = new Map(toleranceByArc);
    if (!growTolerances(rawArcs, oversized, frozen, toleranceByArc)) {
      return { arcs, outlines, tooDetailed: oversized };
    }
  }
}

function buildRegion(
  entry: LabelEntry,
  context: {
    map: LabelMap;
    meta: Record<string, RegionMeta>;
    outlines: Map<number, string>;
    adjacency: Map<number, Set<number>>;
  },
): MapRegion {
  const meta = context.meta[entry.id];
  const neighborLabels = [...(context.adjacency.get(entry.label) ?? [])];
  const neighborIds = neighborLabels
    .map((label) => context.map.entries.find((item) => item.label === label)?.id as string)
    .sort();
  return {
    id: entry.id,
    name: (meta?.name.trim() || `Region ${entry.label}`).slice(0, MAX_NAME_CHARS),
    terrain: meta?.terrain ?? "plain",
    outline: context.outlines.get(entry.label) as string,
    label_point: computeLabelPoint(context.map, entry.label),
    neighbor_ids: neighborIds,
    source_color: entry.sourceColor,
    source_ref: null,
  };
}

function findProblems(
  map: LabelMap,
  counts: Map<number, number>,
  tooDetailed: Set<number>,
  regionCount: number,
): MapProblem[] {
  const problems: MapProblem[] = [];
  if ((counts.get(0) ?? 0) > 0) {
    problems.push({ regionId: null, kind: "unassigned_pixels", detail: `${counts.get(0)} pixels belong to no region` });
  }
  if (regionCount > MAX_REGIONS) {
    problems.push({ regionId: null, kind: "too_detailed", detail: `More than ${MAX_REGIONS} regions` });
  }
  const { sizes, labelOf } = connectedComponents(map.labels, map.width, map.height);
  const pieces = new Map<number, number>();
  labelOf.forEach((label, index) => pieces.set(label, (pieces.get(label) ?? 0) + (sizes[index] > 0 ? 1 : 0)));
  for (const entry of map.entries) {
    if (tooDetailed.has(entry.label)) problems.push({ regionId: entry.id, kind: "too_detailed", detail: "Outline too long to store" });
    if ((pieces.get(entry.label) ?? 0) > 1) problems.push({ regionId: entry.id, kind: "split_color", detail: "One region in several separate pieces" });
  }
  return problems;
}

export function traceLabelMap(
  map: LabelMap,
  meta: Record<string, RegionMeta>,
  options: TraceOptions,
): TraceResult {
  const counts = countPixels(map);
  const entries = map.entries.filter((entry) => (counts.get(entry.label) ?? 0) > 0);
  const rawArcs = extractArcs(map);
  const labels = entries.map((entry) => entry.label);
  const simplified = simplifyUntilFits(rawArcs, labels, options.maxOutlineChars ?? MAX_OUTLINE_CHARS);
  const adjacency = computeAdjacency(rawArcs);
  const context = { map, meta, outlines: simplified.outlines, adjacency };
  const document: MapDocument = {
    schema_version: MAP_SCHEMA_VERSION,
    source: options.source,
    width: map.width,
    height: map.height,
    image_url: options.imageUrl,
    regions: entries.map((entry) => buildRegion(entry, context)),
    roads: [],
  };
  const pixelCounts = Object.fromEntries(entries.map((entry) => [entry.id, counts.get(entry.label) as number]));
  const problems = findProblems(map, counts, simplified.tooDetailed, entries.length);
  return { document, problems, pixelCounts };
}
