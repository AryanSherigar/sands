import React from "react";
import { HeroActions } from "./HeroActions";
import { HeroBadges } from "./HeroBadges";
import { HeroMeta } from "./HeroMeta";
import type { HeroContentProps } from "./HeroContent.types";

export const HeroContent: React.FC<HeroContentProps> = ({ scenario }) => {
  return (
    <div className="relative z-10 mx-auto flex h-full max-w-[1440px] flex-col justify-center px-6">
      <div className="flex max-w-[720px] flex-col items-start">
        <HeroBadges
          primaryGenre={scenario.genre_tags[0]}
          mode={scenario.mode}
          contentTag={scenario.content_tag}
        />
        <h1 className="mb-2 max-w-[18ch] font-display text-hero tracking-[-0.02em] text-content">
          {scenario.title}
        </h1>
        {scenario.logline && (
          <p className="mb-2 max-w-[62ch] font-sans text-base leading-relaxed text-content-muted md:text-[1.0625rem]">
            {scenario.logline}
          </p>
        )}
        <HeroMeta
          estimatedPlaytime={scenario.estimated_playtime}
          ratingAvg={scenario.rating_avg}
          playCount={scenario.play_count}
        />
        <HeroActions
          scenarioId={scenario.scenario_id}
          primaryGenre={scenario.genre_tags[0]}
        />
      </div>
    </div>
  );
};
