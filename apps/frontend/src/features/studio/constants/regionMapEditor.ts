import type { RegionImageRejection } from "@/shared/types/strategy-map.types";
import type { RegionTool } from "../stores/regionMap.store";

export const WAND_TOLERANCE = 32;
export const BRUSH_RADIUS = 6;
export const LASSO_SNAP_RADIUS = 4;
export const PREVIEW_FACTOR = 4;
export const WHEEL_ZOOM_STEP = 1.2;
export const BUTTON_ZOOM_STEP = 1.5;
export const MIN_LASSO_POINTS = 3;
export const MIN_SPLIT_POINTS = 2;

export const TOOL_LABELS: { id: RegionTool; label: string }[] = [
  { id: "select", label: "Select" },
  { id: "merge", label: "Merge" },
  { id: "split", label: "Split" },
  { id: "wand", label: "Wand" },
  { id: "lasso", label: "Lasso" },
  { id: "brush", label: "Brush" },
  { id: "delete", label: "Delete" },
];

export const REJECTION_MESSAGES: Record<RegionImageRejection, string> = {
  not_png: "The region image must be a PNG. JPEG blurs the flat colours.",
  too_large: "The region image is over the 5 MB limit.",
  size_mismatch: "The region image must be exactly the same size as the map picture.",
  decode_failed: "That image could not be read. Try exporting it as PNG again.",
};

export const TRACE_FAILED_MESSAGE = "We could not trace that image. Try again, or trace the map by hand.";
