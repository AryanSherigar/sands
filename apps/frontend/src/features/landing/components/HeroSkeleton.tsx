import React from "react";

export const HeroSkeleton: React.FC = () => (
  <div
    aria-hidden="true"
    className="h-[60dvh] w-full animate-pulse bg-surface-raised md:h-[70vh] md:min-h-[520px] md:max-h-[760px]"
  />
);
