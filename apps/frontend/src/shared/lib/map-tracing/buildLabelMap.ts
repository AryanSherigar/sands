import {
  CLUSTER_TOLERANCE,
  MIN_PIECE_PIXELS,
} from "@/shared/constants/mapTracing";
import type {
  LabelEntry,
  LabelMap,
  PixelImage,
  TraceWarning,
} from "@/shared/types/strategy-map.types";
import {
  bucketKeyOf,
  clusterColors,
  colorDistance,
  type ColorCluster,
  type Rgb,
} from "./clusterColors";
import { connectedComponents, neighbourIndexes } from "./connectedComponents";
import { foldThinClusters } from "./foldThinClusters";
import { smoothLabels } from "./smoothLabels";

interface FoldedColor {
  count: number;
  rgb: Rgb;
}

interface Assignment {
  labels: Uint16Array;
  folded: Map<number, FoldedColor>;
}

const ID_DIGITS = 2;

function toHex(rgb: Rgb): string {
  const parts = rgb.map((value) => value.toString(16).padStart(2, "0"));
  return `#${parts.join("")}`;
}

function nearestCluster(
  clusters: ColorCluster[],
  rgb: Rgb,
): { index: number; distance: number } {
  let best = { index: 0, distance: Infinity };
  clusters.forEach((cluster, index) => {
    const distance = colorDistance(cluster.rgb, rgb);
    if (distance < best.distance) best = { index, distance };
  });
  return best;
}

function assignClusters(image: PixelImage, clusters: ColorCluster[]): Assignment {
  const labels = new Uint16Array(image.width * image.height);
  const folded = new Map<number, FoldedColor>();
  const cache = new Map<number, number>();
  for (let pixel = 0; pixel < labels.length; pixel++) {
    const offset = pixel * 4;
    const rgb: Rgb = [
      image.data[offset],
      image.data[offset + 1],
      image.data[offset + 2],
    ];
    const packed = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2];
    let label = cache.get(packed);
    if (label === undefined) {
      const nearest = nearestCluster(clusters, rgb);
      label = nearest.index + 1;
      cache.set(packed, label);
      if (nearest.distance > CLUSTER_TOLERANCE) rememberFolded(folded, rgb, 0);
    }
    labels[pixel] = label;
    if (!isNearCluster(clusters, label, rgb)) rememberFolded(folded, rgb, 1);
  }
  return { labels, folded };
}

function isNearCluster(
  clusters: ColorCluster[],
  label: number,
  rgb: Rgb,
): boolean {
  return colorDistance(clusters[label - 1].rgb, rgb) <= CLUSTER_TOLERANCE;
}

function rememberFolded(
  folded: Map<number, FoldedColor>,
  rgb: Rgb,
  increment: number,
): void {
  const key = bucketKeyOf(rgb);
  const entry = folded.get(key) ?? { count: 0, rgb };
  entry.count += increment;
  folded.set(key, entry);
}

function mostCommonNeighbour(
  labels: Uint16Array,
  pixels: number[],
  componentId: number,
  context: { ids: Int32Array; width: number; height: number },
): number {
  const tally = new Map<number, number>();
  for (const index of pixels) {
    for (const next of neighbourIndexes(index, context.width, context.height)) {
      if (context.ids[next] === componentId || labels[next] === 0) continue;
      tally.set(labels[next], (tally.get(labels[next]) ?? 0) + 1);
    }
  }
  const ranked = [...tally.entries()].sort(
    (first, second) => second[1] - first[1] || first[0] - second[0],
  );
  return ranked.length > 0 ? ranked[0][0] : 0;
}

function smallComponentPixels(ids: Int32Array, sizes: number[]): Map<number, number[]> {
  const pixelsByComponent = new Map<number, number[]>();
  ids.forEach((componentId, index) => {
    if (componentId < 0 || sizes[componentId] >= MIN_PIECE_PIXELS) return;
    const list = pixelsByComponent.get(componentId) ?? [];
    list.push(index);
    pixelsByComponent.set(componentId, list);
  });
  return pixelsByComponent;
}

function foldTinyPieces(
  labels: Uint16Array,
  size: { width: number; height: number },
  protectedLabels: Set<number>,
): number {
  const { ids, sizes, labelOf } = connectedComponents(labels, size.width, size.height);
  let foldedCount = 0;
  for (const [componentId, pixels] of smallComponentPixels(ids, sizes)) {
    if (protectedLabels.has(labelOf[componentId])) continue;
    const target = mostCommonNeighbour(labels, pixels, componentId, { ids, ...size });
    if (target === 0) continue;
    pixels.forEach((index) => (labels[index] = target));
    foldedCount++;
  }
  return foldedCount;
}

function buildEntries(
  labels: Uint16Array,
  clusters: ColorCluster[],
): { entries: LabelEntry[]; remap: Map<number, number> } {
  const counts = new Map<number, number>();
  labels.forEach((label) => counts.set(label, (counts.get(label) ?? 0) + 1));
  const used = [...counts.keys()]
    .filter((label) => label !== 0)
    .sort((first, second) => {
      const diff = (counts.get(second) ?? 0) - (counts.get(first) ?? 0);
      return diff || toHex(clusters[first - 1].rgb).localeCompare(toHex(clusters[second - 1].rgb));
    });
  const remap = new Map<number, number>();
  const entries = used.map((oldLabel, index) => {
    remap.set(oldLabel, index + 1);
    return {
      label: index + 1,
      id: `region_${String(index + 1).padStart(ID_DIGITS, "0")}`,
      sourceColor: toHex(clusters[oldLabel - 1].rgb),
    };
  });
  return { entries, remap };
}

function describeFolded(folded: Map<number, FoldedColor>): TraceWarning[] {
  return [...folded.entries()]
    .filter(([, color]) => color.count >= MIN_PIECE_PIXELS)
    .sort((first, second) => first[0] - second[0])
    .map(([, color]) => ({
      kind: "folded_color" as const,
      detail: `${toHex(color.rgb)} (${color.count} px) was merged into a neighbouring colour`,
      rgb: color.rgb,
    }));
}

function describeThin(
  thin: Map<number, number>,
  clusters: ColorCluster[],
): TraceWarning[] {
  return [...thin.entries()]
    .filter(([, count]) => count >= MIN_PIECE_PIXELS)
    .sort((first, second) => first[0] - second[0])
    .map(([label, count]) => ({
      kind: "folded_color" as const,
      detail: `${toHex(clusters[label - 1].rgb)} (${count} px) looked like an edge blur and was merged`,
      rgb: clusters[label - 1].rgb,
    }));
}

export function buildLabelMap(
  image: PixelImage,
  extraSeeds: Rgb[] = [],
): { labelMap: LabelMap; warnings: TraceWarning[] } {
  if (image.data.length !== image.width * image.height * 4) {
    throw new Error("Pixel data length does not match image size");
  }
  const clusters = clusterColors(image, extraSeeds);
  const size = { width: image.width, height: image.height };
  const { labels: assigned, folded } = assignClusters(image, clusters);
  const labels = smoothLabels(assigned, image.width, image.height);
  const protectedLabels = new Set(extraSeeds.map((_, index) => index + 1));
  const thin = foldThinClusters(labels, size, protectedLabels);
  const foldedPieces = foldTinyPieces(labels, size, protectedLabels);
  const { entries, remap } = buildEntries(labels, clusters);
  const finalLabels = labels.map((label) => remap.get(label) ?? 0);
  const warnings = [...describeFolded(folded), ...describeThin(thin, clusters)];
  if (foldedPieces > 0) {
    warnings.push({
      kind: "tiny_piece",
      detail: `${foldedPieces} tiny pieces were merged into neighbouring regions`,
    });
  }
  return {
    labelMap: {
      ...size,
      labels: finalLabels,
      entries,
      nextIdNumber: entries.length + 1,
    },
    warnings,
  };
}
