// Frontend mirror of packages/strategy-contracts/strategy_contracts/map.py,
// plus the raster/tracing shapes the Studio map editor works on.

export type Terrain =
  | "plain"
  | "hills"
  | "mountain"
  | "forest"
  | "marsh"
  | "desert"
  | "coast";

type MapSource = "color_image" | "azgaar" | "manual";

export interface Point {
  x: number;
  y: number;
}

export interface MapRegion {
  id: string;
  name: string;
  terrain: Terrain;
  outline: string;
  label_point: Point;
  neighbor_ids: string[];
  source_color: string | null;
  source_ref: string | null;
}

interface MapRoad {
  region_a: string;
  region_b: string;
}

export interface MapDocument {
  schema_version: number;
  source: MapSource;
  width: number;
  height: number;
  image_url: string | null;
  regions: MapRegion[];
  roads: MapRoad[];
}

export interface PixelImage {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}

export interface LabelEntry {
  label: number;
  id: string;
  sourceColor: string | null;
}

export interface LabelMap {
  width: number;
  height: number;
  /** One entry per pixel; 0 means unassigned. */
  labels: Uint16Array;
  entries: LabelEntry[];
  nextIdNumber: number;
}

export interface RegionMeta {
  name: string;
  terrain: Terrain | null;
}

type TraceWarningKind = "folded_color" | "tiny_piece";

export interface TraceWarning {
  kind: TraceWarningKind;
  detail: string;
  /** Present on folded_color warnings so the colour can be promoted to a seed. */
  rgb?: [number, number, number];
}

export type MapProblemKind =
  | "unnamed"
  | "no_terrain"
  | "tiny"
  | "disconnected"
  | "one_way_link"
  | "too_detailed"
  | "unassigned_pixels"
  | "split_color"
  | "few_regions";

export interface MapProblem {
  regionId: string | null;
  kind: MapProblemKind;
  detail: string;
}

export interface TraceResult {
  document: MapDocument;
  problems: MapProblem[];
  pixelCounts: Record<string, number>;
}

export interface TraceOptions {
  source: "color_image" | "manual";
  imageUrl: string | null;
  /** Test hook: overrides the contract outline limit. */
  maxOutlineChars?: number;
}

/** @public Reserved for the future automatic region proposer (SAM). */
export interface LabelMask {
  width: number;
  height: number;
  mask: Uint8Array;
}

/**
 * @public Seam for a future automatic region proposer (SAM); never called yet.
 */
export type RegionProposer = (image: PixelImage) => Promise<LabelMask[]>;

export interface Arc {
  id: number;
  /** Labels on each side when walking the arc in point order (0 = outside). */
  left: number;
  right: number;
  /** Pixel-grid corner coordinates; closed arcs do not repeat the first point. */
  points: Point[];
  isClosed: boolean;
}

export type TraceWorkerRequest =
  | { type: "trace-image"; image: PixelImage; extraSeeds: [number, number, number][]; options: TraceOptions }
  | { type: "trace-map"; labelMap: LabelMap; meta: Record<string, RegionMeta>; options: TraceOptions };

export type TraceWorkerResponse =
  | { type: "progress"; stage: string }
  | { type: "done-image"; labelMap: LabelMap; warnings: TraceWarning[]; result: TraceResult }
  | { type: "done-map"; result: TraceResult }
  | { type: "error"; message: string };

export type RegionImageRejection =
  | "not_png"
  | "too_large"
  | "size_mismatch"
  | "decode_failed";

export interface DecodedRegionImage {
  image: PixelImage;
  originalSize: { width: number; height: number };
}
