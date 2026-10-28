import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { logEvent } from "@/shared/lib/logger";
import { applyMetaToDocument } from "@/shared/lib/map-tracing/applyMeta";
import { createEmptyLabelMap } from "@/shared/lib/map-tracing/editOps";
import {
  checkMap,
  isBlockingProblem,
  isMapFinishable,
} from "@/shared/lib/map-tracing/mapChecks";
import { fitToTraceSide } from "@/shared/lib/map-tracing/traceSize";
import type {
  MapProblem,
  PixelImage,
  TraceWarning,
} from "@/shared/types/strategy-map.types";
import {
  BUTTON_ZOOM_STEP,
  REJECTION_MESSAGES,
  TRACE_FAILED_MESSAGE,
  WHEEL_ZOOM_STEP,
} from "../../constants/regionMapEditor";
import { usePicturePixels } from "../../hooks/usePicturePixels";
import { useTraceMap } from "../../hooks/useTraceMap";
import { useRegionMapStore } from "../../stores/regionMap.store";
import { ProblemList } from "./ProblemList";
import { RegionCanvas } from "./RegionCanvas";
import type { RegionMapEditorProps } from "./RegionMapEditor.types";
import { RegionPanel } from "./RegionPanel";
import { StartChooser } from "./StartChooser";
import { ToolPalette } from "./ToolPalette";
import { useRegionTools } from "./useRegionTools";
import { useRegionTrace } from "./useRegionTrace";
import { useViewport } from "./useViewport";

const FOCUS_ZOOM = 3;
const MAP_ORIGIN = { x: 0, y: 0 };

function summarize(regionCount: number, problems: MapProblem[]): string {
  const attention = new Set(
    problems.filter(isBlockingProblem).flatMap((problem) => (problem.regionId ? [problem.regionId] : [])),
  );
  const noun = regionCount === 1 ? "region" : "regions";
  return `${regionCount} ${noun} found, ${attention.size} need attention`;
}

export const RegionMapEditor: React.FC<RegionMapEditorProps> = ({
  pictureUrl,
  pictureSize,
  initialDocument,
  onFinish,
}) => {
  const raster = useMemo(
    () => fitToTraceSide({ width: pictureSize.width, height: pictureSize.height }),
    [pictureSize.width, pictureSize.height],
  );
  const store = useRegionMapStore();
  const { traceColorImage, traceImage, retrace } = useTraceMap();
  const { pixels } = usePicturePixels(pictureUrl, raster);
  const [source, setSource] = useState<"color_image" | "manual">("manual");
  const [startError, setStartError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [warnings, setWarnings] = useState<TraceWarning[]>([]);
  const [focusSignal, setFocusSignal] = useState(0);
  const sourceImageRef = useRef<PixelImage | null>(null);
  const seedsRef = useRef<[number, number, number][]>([]);
  const viewport = useViewport(raster);
  const { trace, setDraftMap } = useRegionTrace(store.labelMap, { source, imageUrl: pictureUrl }, retrace);
  const tools = useRegionTools({
    picture: pixels,
    setDraftMap,
    onRegionCreated: () => setFocusSignal((signal) => signal + 1),
  });

  useEffect(() => () => useRegionMapStore.getState().reset(), []);

  useEffect(() => {
    if (!initialDocument) return;
    useRegionMapStore.getState().loadFromDocument(initialDocument);
    setSource(initialDocument.source === "color_image" ? "color_image" : "manual");
  }, [initialDocument]);

  const document = useMemo(
    () => (trace ? applyMetaToDocument(trace.document, store.meta) : null),
    [trace, store.meta],
  );
  const problems = useMemo(
    () => (trace && document ? [...trace.problems, ...checkMap(document, store.meta, trace.pixelCounts)] : []),
    [trace, document, store.meta],
  );
  const regionNameById = useMemo(
    () => Object.fromEntries((document?.regions ?? []).map((region) => [region.id, region.name])),
    [document],
  );

  const handleColorImageChosen = async (file: File): Promise<void> => {
    setStartError(null);
    setIsStarting(true);
    const outcome = await traceColorImage(file, pictureSize)
      .catch((error: unknown) => {
        logEvent("error", "region_map_start_failed", { message: error instanceof Error ? error.message : "unknown" });
        return null;
      })
      .finally(() => setIsStarting(false));
    if (!outcome) {
      setStartError(TRACE_FAILED_MESSAGE);
      return;
    }
    if (!outcome.ok) {
      setStartError(REJECTION_MESSAGES[outcome.reason]);
      return;
    }
    sourceImageRef.current = outcome.image;
    seedsRef.current = [];
    setWarnings(outcome.warnings);
    setSource("color_image");
    store.loadFromTrace(outcome.labelMap);
  };

  const handleTraceByHand = (): void => {
    setSource("manual");
    store.loadFromTrace(createEmptyLabelMap(raster.width, raster.height));
  };

  const handleKeepColor = async (rgb: [number, number, number]): Promise<void> => {
    if (!sourceImageRef.current) return;
    const seeds = [...seedsRef.current, rgb];
    const traced = await traceImage(sourceImageRef.current, seeds).catch((error: unknown) => {
      logEvent("error", "region_map_keep_color_failed", { message: error instanceof Error ? error.message : "unknown" });
      return null;
    });
    if (!traced) return;
    seedsRef.current = seeds;
    setWarnings(traced.warnings);
    store.loadFromTrace(traced.labelMap);
  };

  const handleSelectProblemRegion = (regionId: string): void => {
    store.select(regionId);
    const region = document?.regions.find((item) => item.id === regionId);
    if (!region || !document) return;
    viewport.zoomTo(
      {
        x: (region.label_point.x * raster.width) / document.width,
        y: (region.label_point.y * raster.height) / document.height,
      },
      FOCUS_ZOOM,
    );
  };

  const handleDone = (): void => {
    if (document) onFinish({ document, capitalRegionIds: store.capitalRegionIds });
  };

  if (!store.labelMap) {
    return (
      <StartChooser
        errorMessage={startError}
        isBusy={isStarting}
        onColorImageChosen={handleColorImageChosen}
        onTraceByHand={handleTraceByHand}
      />
    );
  }

  const regionCount = document?.regions.length ?? 0;
  const isFinishable = regionCount > 0 && isMapFinishable(problems);
  const hasEdits = store.past.length > 0 || Object.keys(store.meta).length > 0;
  const selectedMeta = store.selectedId ? store.meta[store.selectedId] : undefined;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-3">
        <ToolPalette
          tool={store.tool}
          canUndo={store.past.length > 0}
          canRedo={store.future.length > 0}
          onToolChange={store.setTool}
          onUndo={store.undo}
          onRedo={store.redo}
          onNewRegion={() => store.select(null)}
          onZoomIn={() => viewport.zoomBy(MAP_ORIGIN, BUTTON_ZOOM_STEP)}
          onZoomOut={() => viewport.zoomBy(MAP_ORIGIN, 1 / BUTTON_ZOOM_STEP)}
          onFit={viewport.reset}
        />
        <RegionCanvas
          pictureUrl={pictureUrl}
          raster={raster}
          document={document}
          selectedIds={store.selectedIds}
          tool={store.tool}
          viewBox={viewport.viewBox}
          dragPoints={tools.dragPoints}
          onRegionClick={(regionId, event) => tools.handleRegionClick(regionId, event)}
          onToolMouseDown={tools.handleCanvasMouseDown}
          onToolMouseMove={tools.handleCanvasMouseMove}
          onToolMouseUp={tools.handleCanvasMouseUp}
          onWheelZoom={(point, isZoomingIn) =>
            viewport.zoomBy(point, isZoomingIn ? WHEEL_ZOOM_STEP : 1 / WHEEL_ZOOM_STEP)
          }
          onPan={viewport.panBy}
        />
      </div>
      <aside className="space-y-4">
        <p className="text-sm font-medium text-content">{summarize(regionCount, problems)}</p>
        <RegionPanel
          regionId={store.selectedId}
          name={selectedMeta?.name ?? ""}
          terrain={selectedMeta?.terrain ?? null}
          isCapital={store.selectedId ? store.capitalRegionIds.includes(store.selectedId) : false}
          selectedCount={store.selectedIds.length}
          focusSignal={focusSignal}
          onNameChange={(name) => store.selectedId && store.setMeta(store.selectedId, { name })}
          onTerrainChange={(terrain) => store.selectedId && store.setMeta(store.selectedId, { terrain })}
          onCapitalChange={() => store.selectedId && store.toggleCapital(store.selectedId)}
          onBulkTerrainChange={(terrain) => store.setBulkTerrain(store.selectedIds, terrain)}
        />
        <ProblemList problems={problems} regionNameById={regionNameById} onSelectRegion={handleSelectProblemRegion} />
        {warnings
          .filter((warning) => warning.kind === "folded_color" && warning.rgb)
          .map((warning) => (
            <div key={warning.detail} className="space-y-1 text-sm text-content-muted">
              <p>{warning.detail}</p>
              <Button
                size="sm"
                variant="secondary"
                disabled={hasEdits}
                onClick={() => handleKeepColor(warning.rgb as [number, number, number])}
              >
                Keep as its own region
              </Button>
            </div>
          ))}
        <Button disabled={!isFinishable} onClick={handleDone}>
          Done
        </Button>
        {!isFinishable && regionCount > 0 && (
          <p className="text-xs text-content-muted">Fix the items listed above to finish.</p>
        )}
      </aside>
    </div>
  );
};
