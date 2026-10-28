import React from "react";
import {
  SKELETON_ROW_COUNT,
  TOP_RATED_ROW,
} from "../constants/landing.constants";
import { ContinueRow } from "../components/ContinueRow";
import { FeaturedHero } from "../components/FeaturedHero";
import { FeaturedWorldsGrid } from "../components/FeaturedWorldsGrid";
import { HeroSkeleton } from "../components/HeroSkeleton";
import { LandingEmptyState } from "../components/LandingEmptyState";
import { RowSkeleton } from "../components/RowSkeleton";
import { StudioShowcaseBand } from "../components/StudioShowcaseBand";
import { useLandingRow } from "../hooks/useLandingRow";
import { pickFeaturedScenario } from "../utils/pickFeaturedScenario";
import { resolveCuratedWorlds } from "../utils/resolveCuratedWorlds";

const SKELETON_ROW_KEYS = Array.from(
  { length: SKELETON_ROW_COUNT },
  (_, index) => `skeleton-row-${index}`,
);

export const LandingPage: React.FC = () => {
  const { data, isPending } = useLandingRow(TOP_RATED_ROW);

  if (isPending) {
    return (
      <div className="space-y-10">
        <HeroSkeleton />
        <div className="mx-auto max-w-[1440px] px-6 space-y-10">
          {SKELETON_ROW_KEYS.map((key) => (
            <RowSkeleton key={key} />
          ))}
        </div>
      </div>
    );
  }

  if (data && data.items.length === 0) return <LandingEmptyState />;

  const featured = data ? pickFeaturedScenario(data.items) : null;
  const curatedWorlds = resolveCuratedWorlds(data?.items, featured?.scenario_id);

  return (
    <div className="space-y-12 pb-16">
      {featured && <FeaturedHero scenario={featured} />}
      <div className="mx-auto max-w-[1440px] px-6 space-y-12">
        <ContinueRow />
        {curatedWorlds.length > 0 && (
          <FeaturedWorldsGrid
            scenarios={curatedWorlds}
            totalCount={data?.total_count}
          />
        )}
        <StudioShowcaseBand />
      </div>
    </div>
  );
};
