import React, { useRef } from "react";
import { RegionOutlineLayer } from "@/shared/components/RegionOutlineLayer/RegionOutlineLayer";
import type { Point } from "@/shared/types/strategy-map.types";
import type { RegionCanvasProps } from "./RegionCanvas.types";

function parseViewBox(viewBox: string): { x: number; y: number; width: number; height: number } {
  const [x, y, width, height] = viewBox.split(" ").map(Number);
  return { x, y, width, height };
}

function toRasterPoint(event: React.MouseEvent<SVGSVGElement>, viewBox: string): Point {
  const rect = event.currentTarget.getBoundingClientRect();
  // NOTE: jsdom reports empty rects; treat client coordinates as raster coordinates there.
  if (rect.width === 0 || rect.height === 0) {
    return { x: Math.round(event.clientX), y: Math.round(event.clientY) };
  }
  const box = parseViewBox(viewBox);
  return {
    x: Math.round(box.x + ((event.clientX - rect.left) / rect.width) * box.width),
    y: Math.round(box.y + ((event.clientY - rect.top) / rect.height) * box.height),
  };
}

export const RegionCanvas: React.FC<RegionCanvasProps> = ({
  pictureUrl,
  raster,
  document,
  selectedIds,
  tool,
  viewBox,
  dragPoints,
  onRegionClick,
  onToolMouseDown,
  onToolMouseMove,
  onToolMouseUp,
  onWheelZoom,
  onPan,
}) => {
  const panFromRef = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = (event: React.MouseEvent<SVGSVGElement>): void => {
    const isBackground = event.target === event.currentTarget || (event.target as Element).tagName === "image";
    if (tool === "select" && isBackground) {
      panFromRef.current = { x: event.clientX, y: event.clientY };
      return;
    }
    onToolMouseDown(toRasterPoint(event, viewBox));
  };

  const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>): void => {
    const from = panFromRef.current;
    const rect = event.currentTarget.getBoundingClientRect();
    if (from && rect.width > 0) {
      const box = parseViewBox(viewBox);
      onPan(((from.x - event.clientX) / rect.width) * box.width, ((from.y - event.clientY) / rect.height) * box.height);
      panFromRef.current = { x: event.clientX, y: event.clientY };
      return;
    }
    onToolMouseMove(toRasterPoint(event, viewBox));
  };

  const handleMouseUp = (): void => {
    panFromRef.current = null;
    onToolMouseUp();
  };

  const handleWheel = (event: React.WheelEvent<SVGSVGElement>): void => {
    onWheelZoom(toRasterPoint(event, viewBox), event.deltaY < 0);
  };

  return (
    <svg
      aria-label="Region map"
      viewBox={viewBox}
      className="w-full select-none rounded-md border border-border-strong bg-surface-inset"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      <image href={pictureUrl} width={raster.width} height={raster.height} />
      {document && (
        <RegionOutlineLayer
          document={document}
          targetSize={raster}
          selectedIds={selectedIds}
          showNeighborLinks
          onRegionClick={onRegionClick}
        />
      )}
      {dragPoints.length > 1 && (
        <polyline
          points={dragPoints.map((point) => `${point.x},${point.y}`).join(" ")}
          className="pointer-events-none fill-none stroke-primary stroke-2 [vector-effect:non-scaling-stroke]"
        />
      )}
    </svg>
  );
};
