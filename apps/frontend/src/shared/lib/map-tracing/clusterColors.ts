import {
  CLUSTER_TOLERANCE,
  MIN_SEED_PIXELS,
} from "@/shared/constants/mapTracing";
import type { PixelImage } from "@/shared/types/strategy-map.types";

export type Rgb = [number, number, number];

export interface ColorCluster {
  rgb: Rgb;
  pixelCount: number;
}

const BUCKET_SHIFT = 4;
const BUCKET_BITS = 8 - BUCKET_SHIFT;

interface Bucket {
  key: number;
  count: number;
  sum: Rgb;
}

export function colorDistance(first: Rgb, second: Rgb): number {
  const red = first[0] - second[0];
  const green = first[1] - second[1];
  const blue = first[2] - second[2];
  return Math.sqrt(red * red + green * green + blue * blue);
}

export function bucketKeyOf(rgb: Rgb): number {
  const red = rgb[0] >> BUCKET_SHIFT;
  const green = rgb[1] >> BUCKET_SHIFT;
  const blue = rgb[2] >> BUCKET_SHIFT;
  return (red << (2 * BUCKET_BITS)) | (green << BUCKET_BITS) | blue;
}

function collectBuckets(image: PixelImage): Bucket[] {
  const buckets = new Map<number, Bucket>();
  for (let offset = 0; offset < image.data.length; offset += 4) {
    const rgb: Rgb = [
      image.data[offset],
      image.data[offset + 1],
      image.data[offset + 2],
    ];
    const key = bucketKeyOf(rgb);
    const bucket = buckets.get(key) ?? { key, count: 0, sum: [0, 0, 0] };
    bucket.count++;
    bucket.sum = [
      bucket.sum[0] + rgb[0],
      bucket.sum[1] + rgb[1],
      bucket.sum[2] + rgb[2],
    ];
    buckets.set(key, bucket);
  }
  return [...buckets.values()].sort(
    (first, second) => second.count - first.count || first.key - second.key,
  );
}

function meanOf(bucket: Bucket): Rgb {
  return [
    Math.round(bucket.sum[0] / bucket.count),
    Math.round(bucket.sum[1] / bucket.count),
    Math.round(bucket.sum[2] / bucket.count),
  ];
}

interface Group {
  rgb: Rgb;
  pixelCount: number;
  weightedSum: Rgb;
  isFixed: boolean;
}

function findNearbyGroup(groups: Group[], rgb: Rgb): Group | undefined {
  return groups.find(
    (group) => colorDistance(group.rgb, rgb) <= CLUSTER_TOLERANCE,
  );
}

function addBucketToGroup(group: Group, bucket: Bucket): void {
  group.pixelCount += bucket.count;
  group.weightedSum = [
    group.weightedSum[0] + bucket.sum[0],
    group.weightedSum[1] + bucket.sum[1],
    group.weightedSum[2] + bucket.sum[2],
  ];
}

function groupBuckets(buckets: Bucket[], extraSeeds: Rgb[]): Group[] {
  const groups: Group[] = extraSeeds.map((rgb) => ({
    rgb,
    pixelCount: 0,
    weightedSum: [0, 0, 0],
    isFixed: true,
  }));
  for (const bucket of buckets) {
    const rgb = meanOf(bucket);
    let group = findNearbyGroup(groups, rgb);
    if (!group) {
      group = { rgb, pixelCount: 0, weightedSum: [0, 0, 0], isFixed: false };
      groups.push(group);
    }
    addBucketToGroup(group, bucket);
  }
  return groups;
}

function centreOf(group: Group): Rgb {
  if (group.isFixed || group.pixelCount === 0) return group.rgb;
  return [
    Math.round(group.weightedSum[0] / group.pixelCount),
    Math.round(group.weightedSum[1] / group.pixelCount),
    Math.round(group.weightedSum[2] / group.pixelCount),
  ];
}

export function clusterColors(
  image: PixelImage,
  extraSeeds: Rgb[] = [],
): ColorCluster[] {
  return groupBuckets(collectBuckets(image), extraSeeds)
    .filter((group) => group.isFixed || group.pixelCount >= MIN_SEED_PIXELS)
    .map((group) => ({ rgb: centreOf(group), pixelCount: group.pixelCount }));
}
