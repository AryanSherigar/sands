import { MAX_NAME_CHARS } from "@/shared/constants/mapTracing";
import type { MapDocument, RegionMeta } from "@/shared/types/strategy-map.types";

export function applyMetaToDocument(
  document: MapDocument,
  meta: Record<string, RegionMeta>,
): MapDocument {
  return {
    ...document,
    regions: document.regions.map((region) => {
      const entry = meta[region.id];
      const name = entry?.name.trim().slice(0, MAX_NAME_CHARS);
      return { ...region, name: name || region.name, terrain: entry?.terrain ?? region.terrain };
    }),
  };
}
