import React, { useRef } from "react";
import {
  TransformWrapper,
  TransformComponent,
  type ReactZoomPanPinchRef,
} from "react-zoom-pan-pinch";
import { StrategyMapCanvas } from "./StrategyMapCanvas";
import type { StrategyMapViewportProps } from "./StrategyMap.types";

const INITIAL_SCALE = 1;
const MIN_SCALE = 0.5;
const MAX_SCALE = 3;
const WHEEL_STEP = 0.1;

export const StrategyMapViewport: React.FC<StrategyMapViewportProps> = ({
  onControlsReady,
  ...canvasProps
}) => {
  const transformRef = useRef<ReactZoomPanPinchRef>(null);

  return (
    <div className="w-full h-full overflow-hidden bg-[#F3EAD3]">
      <TransformWrapper
        ref={transformRef}
        initialScale={INITIAL_SCALE}
        minScale={MIN_SCALE}
        maxScale={MAX_SCALE}
        wheel={{ step: WHEEL_STEP }}
        doubleClick={{ disabled: true }}
        onInit={onControlsReady}
      >
        <TransformComponent wrapperClass="w-full h-full" contentClass="w-full h-full">
          <StrategyMapCanvas {...canvasProps} />
        </TransformComponent>
      </TransformWrapper>
    </div>
  );
};
