import type { MapDocument } from "@/shared/types/strategy-map.types";

export const EMPTY_STRATEGY_MAP: MapDocument = {
  schema_version: 1,
  source: "manual",
  width: 1600,
  height: 900,
  image_url: null,
  regions: [],
  roads: [],
};
