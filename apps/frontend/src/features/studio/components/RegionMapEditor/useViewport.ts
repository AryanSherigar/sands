import { useCallback, useState } from "react";
import type { Point } from "@/shared/types/strategy-map.types";

interface Size {
  width: number;
  height: number;
}

interface Box extends Size {
  x: number;
  y: number;
}

const MAX_ZOOM = 16;

function clampBox(box: Box, size: Size): Box {
  return {
    ...box,
    x: Math.round(Math.min(Math.max(0, box.x), size.width - box.width)),
    y: Math.round(Math.min(Math.max(0, box.y), size.height - box.height)),
  };
}

export function useViewport(size: Size) {
  const whole: Box = { x: 0, y: 0, width: size.width, height: size.height };
  const [box, setBox] = useState<Box>(whole);
  const scale = size.width / box.width;

  const zoomTo = useCallback(
    (point: Point, factor: number): void => {
      const zoom = Math.min(MAX_ZOOM, Math.max(1, factor));
      const width = Math.round(size.width / zoom);
      const height = Math.round(size.height / zoom);
      setBox(clampBox({ x: point.x - width / 2, y: point.y - height / 2, width, height }, size));
    },
    [size],
  );

  const zoomBy = useCallback(
    (point: Point, factor: number): void => zoomTo(point, scale * factor),
    [scale, zoomTo],
  );

  const panBy = useCallback(
    (dx: number, dy: number): void =>
      setBox((current) => clampBox({ ...current, x: current.x + dx, y: current.y + dy }, size)),
    [size],
  );

  const reset = useCallback((): void => setBox({ x: 0, y: 0, width: size.width, height: size.height }), [size]);

  return { viewBox: `${box.x} ${box.y} ${box.width} ${box.height}`, box, zoomTo, zoomBy, panBy, reset };
}
