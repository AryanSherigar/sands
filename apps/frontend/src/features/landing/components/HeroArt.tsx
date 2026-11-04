import React, { useState } from "react";
import { cn } from "@/shared/lib/cn";
import type { HeroArtProps } from "./HeroArt.types";

export const HeroArt: React.FC<HeroArtProps> = ({ coverImageUrl }) => {
  const [isLoaded, setIsLoaded] = useState(false);

  const handleLoad = (): void => setIsLoaded(true);

  return (
    <div className="absolute inset-0 overflow-hidden bg-neutral-900">
      <img
        src={coverImageUrl}
        alt=""
        // @ts-expect-error standard HTML fetchpriority attribute
        fetchpriority="high"
        decoding="async"
        onLoad={handleLoad}
        className={cn(
          "h-full w-full object-cover opacity-0 transition-opacity duration-base",
          isLoaded && "opacity-100",
        )}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
      <div className="absolute inset-0 w-full bg-gradient-to-r from-black/70 via-black/35 to-transparent md:w-3/4" />
    </div>
  );
};
