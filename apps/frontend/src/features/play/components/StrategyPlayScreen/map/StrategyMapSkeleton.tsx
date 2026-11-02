import React from "react";
import type { StrategyMapSkeletonProps } from "./StrategyMapSkeleton.types";

const MapContourPaths: React.FC = () => (
  <svg
    className="absolute inset-0 w-full h-full opacity-15 pointer-events-none"
    viewBox="0 0 800 600"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M 100 300 C 200 150 400 200 500 100 C 600 200 700 250 750 400 C 700 550 500 500 400 550 Z"
      stroke="#8C7A6B"
      strokeWidth="2"
      strokeDasharray="6 6"
      className="animate-pulse"
    />
    <path
      d="M 180 320 C 260 200 420 250 480 180 C 560 250 630 300 660 410 C 610 500 460 460 380 490 Z"
      stroke="#8C7A6B"
      strokeWidth="1.5"
      className="animate-pulse"
    />
  </svg>
);

export const StrategyMapSkeleton: React.FC<StrategyMapSkeletonProps> = ({
  className,
  message = "Unfurling realm cartography...",
}) => {
  return (
    <div
      data-testid="strategy-map-skeleton"
      role="status"
      aria-label="Loading map"
      className={`absolute inset-0 flex flex-col items-center justify-center bg-[#ECE4D0] overflow-hidden select-none pointer-events-none ${
        className ?? ""
      }`}
    >
      <MapContourPaths />
      <div className="relative z-10 flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-full border-2 border-[#8C7A6B]/30 border-t-[#8C7A6B] animate-spin mb-3" />
        <span className="font-serif italic text-sm text-[#5C4D3C]">{message}</span>
      </div>
    </div>
  );
};
