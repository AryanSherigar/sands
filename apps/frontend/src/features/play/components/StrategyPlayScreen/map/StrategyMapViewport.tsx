import React, { useLayoutEffect, useRef, useState } from "react";
import {
  TransformWrapper,
  TransformComponent,
} from "react-zoom-pan-pinch";
import { StrategyMapCanvas } from "./StrategyMapCanvas";
import type { StrategyMapViewportProps } from "./StrategyMap.types";

const INITIAL_SCALE = 1;
const MIN_SCALE = 0.5;
const MAX_SCALE = 3;
const WHEEL_STEP = 0.1;

const computeFitScale = (
  container: { width: number; height: number },
  map: { width: number; height: number },
): number => {
  if (!container.width || !container.height || !map.width || !map.height) return INITIAL_SCALE;
  const fit = Math.min(container.width / map.width, container.height / map.height);
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, fit));
};

const EmptyMapNotice: React.FC = () => (
  <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center select-none pointer-events-none">
    <p className="font-serif text-lg font-semibold text-[#5C4D3C]">
      No realm cartography available
    </p>
    <p className="font-serif italic text-sm text-[#8C7A6B] mt-1">
      This scenario has no tactical map surveyed.
    </p>
  </div>
);

export const StrategyMapViewport: React.FC<StrategyMapViewportProps> = ({
  onControlsReady,
  ...canvasProps
}) => {
  const hasNoRegions = canvasProps.document.regions.length === 0;
  const containerRef = useRef<HTMLDivElement>(null);
  const [fitScale, setFitScale] = useState<number | null>(null);
  const { width: mapWidth, height: mapHeight } = canvasProps.document;

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    setFitScale(
      computeFitScale(
        { width: container.clientWidth, height: container.clientHeight },
        { width: mapWidth, height: mapHeight },
      ),
    );
  }, [mapWidth, mapHeight]);

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-hidden bg-[#F3EAD3]">
      {fitScale === null ? null : (
        <TransformWrapper
          key={`${mapWidth}x${mapHeight}`}
          initialScale={fitScale}
          centerOnInit
          minScale={Math.min(MIN_SCALE, fitScale)}
          maxScale={MAX_SCALE}
          wheel={{ step: WHEEL_STEP }}
          doubleClick={{ disabled: true }}
          onInit={onControlsReady}
        >
          {/* NOTE: the library's own unlayered CSS sizes its wrapper to fit-content and beats unimportant Tailwind utilities, which clipped every zoom to the map's native box. */}
          <TransformComponent wrapperClass="w-full! h-full!">
            <StrategyMapCanvas {...canvasProps} />
          </TransformComponent>
        </TransformWrapper>
      )}
      {hasNoRegions && <EmptyMapNotice />}
    </div>
  );
};
