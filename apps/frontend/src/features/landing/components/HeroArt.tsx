import React, { useState } from "react";
import { cn } from "@/shared/lib/cn";
import type { HeroArtProps } from "./HeroArt.types";

export const HeroArt: React.FC<HeroArtProps> = ({ coverImageUrl }) => {
  const [isLoaded, setIsLoaded] = useState(false);

  const handleLoad = (): void => setIsLoaded(true);

  return (
    <div className="absolute inset-0 overflow-hidden bg-surface-sunken">
      <img
        src={coverImageUrl}
        alt=""
        // @ts-expect-error standard HTML fetchpriority attribute
        fetchpriority="high"
        decoding="async"
        onLoad={handleLoad}
        className={cn(
          "h-full w-full object-cover opacity-0 transition-opacity duration-base",
          isLoaded && "opacity-80",
        )}
      />
      {/* Multi-layer Tonal Scrim for Cinematic Contrast */}
      <div className="absolute inset-0 bg-linear-to-t from-surface/30 via-surface/15 to-transparent" />
      <div className="absolute inset-0 bg-linear-to-r from-surface/40 via-surface/20 to-transparent w-full md:w-3/4" />
    </div>
  );
};
