import React from "react";
import { HeroArt } from "./HeroArt";
import { HeroContent } from "./HeroContent";
import { resolveCoverImage } from "../utils/resolveCoverImage";
import type { FeaturedHeroProps } from "./FeaturedHero.types";

export const FeaturedHero: React.FC<FeaturedHeroProps> = ({ scenario }) => {
  return (
    <section
      aria-label="Featured story"
      className="relative isolate w-full h-[80vh] min-h-[580px] max-h-[880px]"
    >
      <HeroArt
        coverImageUrl={resolveCoverImage(
          scenario.cover_image_url,
          scenario.scenario_id,
        )}
      />
      <HeroContent scenario={scenario} />
    </section>
  );
};
