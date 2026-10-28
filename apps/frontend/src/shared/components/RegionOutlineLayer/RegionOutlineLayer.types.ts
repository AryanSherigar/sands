import type { MouseEvent } from "react";
import type { MapDocument } from "@/shared/types/strategy-map.types";

export interface RegionOutlineLayerProps {
  document: MapDocument;
  /** Size of the picture space the layer is drawn into; outlines are scaled to it. */
  targetSize: { width: number; height: number };
  selectedIds: string[];
  /** Fill class per region id; regions without an entry keep the default tint cycle. */
  regionFillClasses?: Record<string, string>;
  showNeighborLinks?: boolean;
  onRegionClick?: (regionId: string, event: MouseEvent<SVGPathElement>) => void;
}
