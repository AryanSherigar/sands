import type { Terrain } from "@/shared/types/strategy-map.types";

export const CLUSTER_TOLERANCE = 40;
export const MIN_SEED_PIXELS = 300;
export const MIN_PIECE_PIXELS = 12;
export const MIN_SHARED_BORDER = 8;
export const START_SIMPLIFY_TOLERANCE = 1.5;
export const SIMPLIFY_GROWTH = 1.5;
export const MAX_SIMPLIFY_TOLERANCE = 16;
export const MAX_TRACE_SIDE = 2048;
export const TINY_REGION_PIXELS = 400;
export const RECOMMENDED_MIN_REGIONS = 20;
export const UNDO_DEPTH = 30;

export const MAP_SCHEMA_VERSION = 1;
export const MAX_REGIONS = 200;
export const MAX_OUTLINE_CHARS = 20000;
export const MAX_NAME_CHARS = 80;

export const TERRAINS: readonly Terrain[] = [
  "plain",
  "hills",
  "mountain",
  "forest",
  "marsh",
  "desert",
  "coast",
];

export const MAX_REGION_IMAGE_BYTES = 5 * 1024 * 1024;
export const REGION_IMAGE_TYPE = "image/png";

export const SMOOTH_RADIUS = 2;

/** Half-width (in pixels) below which a colour cluster is treated as an edge blur, not a region. */
export const MIN_REGION_THICKNESS = 12;
