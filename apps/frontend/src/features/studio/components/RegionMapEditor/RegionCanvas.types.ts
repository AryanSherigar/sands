import type { MouseEvent } from "react";
import type { MapDocument, Point } from "@/shared/types/strategy-map.types";
import type { RegionTool } from "../../stores/regionMap.store";

export interface RegionCanvasProps {
  pictureUrl: string;
  raster: { width: number; height: number };
  document: MapDocument | null;
  selectedIds: string[];
  tool: RegionTool;
  viewBox: string;
  dragPoints: Point[];
  onRegionClick: (regionId: string, event: MouseEvent<SVGPathElement>) => void;
  onToolMouseDown: (point: Point) => void;
  onToolMouseMove: (point: Point) => void;
  onToolMouseUp: () => void;
  onWheelZoom: (point: Point, isZoomingIn: boolean) => void;
  onPan: (dx: number, dy: number) => void;
}
