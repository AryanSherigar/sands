import { useMemo, useRef, useState } from "react";
import {
  addRegion,
  deleteRegion,
  mergeRegions,
  paintBrush,
  paintMask,
  splitRegion,
} from "@/shared/lib/map-tracing/editOps";
import {
  edgeStrength,
  floodSelect,
  polygonMask,
  snapToEdge,
} from "@/shared/lib/map-tracing/wandAndLasso";
import type {
  LabelMap,
  PixelImage,
  Point,
} from "@/shared/types/strategy-map.types";
import {
  BRUSH_RADIUS,
  LASSO_SNAP_RADIUS,
  MIN_LASSO_POINTS,
  MIN_SPLIT_POINTS,
  WAND_TOLERANCE,
} from "../../constants/regionMapEditor";
import { useRegionMapStore } from "../../stores/regionMap.store";

interface ToolArgs {
  picture: PixelImage | null;
  setDraftMap: (map: LabelMap | null) => void;
  onRegionCreated: (id: string) => void;
}

interface ClickModifiers {
  ctrlKey: boolean;
  metaKey: boolean;
}

function idAtPoint(map: LabelMap, point: Point): string | null {
  const inside = point.x >= 0 && point.y >= 0 && point.x < map.width && point.y < map.height;
  if (!inside) return null;
  const label = map.labels[point.y * map.width + point.x];
  return map.entries.find((entry) => entry.label === label)?.id ?? null;
}

function countPixels(map: LabelMap, id: string): number {
  const label = map.entries.find((entry) => entry.id === id)?.label ?? -1;
  return map.labels.filter((value) => value === label).length;
}

export function useRegionTools({ picture, setDraftMap, onRegionCreated }: ToolArgs) {
  const labelMap = useRegionMapStore((state) => state.labelMap);
  const tool = useRegionMapStore((state) => state.tool);
  const selectedId = useRegionMapStore((state) => state.selectedId);
  const selectedIds = useRegionMapStore((state) => state.selectedIds);
  const store = useRegionMapStore.getState();
  const strength = useMemo(() => (picture ? edgeStrength(picture) : null), [picture]);
  const [dragPoints, setDragPoints] = useState<Point[]>([]);
  const draftRef = useRef<LabelMap | null>(null);

  const assignMask = (mask: Uint8Array): void => {
    if (!labelMap) return;
    if (selectedId) {
      store.applyEdit(paintMask(labelMap, mask, selectedId));
      return;
    }
    const created = addRegion(labelMap, mask, null);
    store.applyEdit(created.map);
    store.select(created.id);
    onRegionCreated(created.id);
  };

  const handleRegionClick = (regionId: string, modifiers: ClickModifiers): void => {
    if (!labelMap) return;
    if (tool === "delete") store.applyEdit(deleteRegion(labelMap, regionId));
    else if (tool === "merge" && selectedId && selectedId !== regionId) {
      const isSelectedLarger = countPixels(labelMap, selectedId) >= countPixels(labelMap, regionId);
      const [keep, remove] = isSelectedLarger ? [selectedId, regionId] : [regionId, selectedId];
      store.applyEdit(mergeRegions(labelMap, keep, remove));
      store.select(keep);
    } else if (modifiers.ctrlKey || modifiers.metaKey) {
      const isPicked = selectedIds.includes(regionId);
      store.setSelectedIds(isPicked ? selectedIds.filter((id) => id !== regionId) : [...selectedIds, regionId]);
    } else store.select(regionId);
  };

  const paintDraft = (point: Point): void => {
    if (!labelMap || !selectedId) return;
    draftRef.current = paintBrush(draftRef.current ?? labelMap, point, BRUSH_RADIUS, selectedId);
    setDraftMap(draftRef.current);
  };

  const handleCanvasMouseDown = (point: Point): void => {
    if (!labelMap) return;
    if (tool === "wand" && picture) assignMask(floodSelect(picture, point, WAND_TOLERANCE));
    else if (tool === "brush") paintDraft(point);
    else if (tool === "lasso" || tool === "split") setDragPoints([point]);
  };

  const handleCanvasMouseMove = (point: Point): void => {
    if (tool === "brush" && draftRef.current) paintDraft(point);
    const isLassoLike = tool === "lasso" || tool === "split";
    if (!isLassoLike || dragPoints.length === 0) return;
    const next = tool === "lasso" && strength && picture ? snapToEdge(strength, picture.width, point, LASSO_SNAP_RADIUS) : point;
    setDragPoints((points) => [...points, next]);
  };

  const finishLasso = (): void => {
    if (!labelMap || !picture || dragPoints.length < MIN_LASSO_POINTS) return;
    assignMask(polygonMask(labelMap.width, labelMap.height, dragPoints));
  };

  const finishSplit = (): void => {
    if (!labelMap || dragPoints.length < MIN_SPLIT_POINTS) return;
    const targetId = idAtPoint(labelMap, dragPoints[0]);
    if (targetId) store.applyEdit(splitRegion(labelMap, targetId, dragPoints));
  };

  const handleCanvasMouseUp = (): void => {
    if (tool === "brush" && draftRef.current) store.applyEdit(draftRef.current);
    if (tool === "lasso") finishLasso();
    if (tool === "split") finishSplit();
    draftRef.current = null;
    setDraftMap(null);
    setDragPoints([]);
  };

  return { dragPoints, handleRegionClick, handleCanvasMouseDown, handleCanvasMouseMove, handleCanvasMouseUp };
}
