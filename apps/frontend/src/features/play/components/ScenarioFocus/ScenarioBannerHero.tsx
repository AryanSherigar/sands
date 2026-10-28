import React from "react";
import { GenreChips } from "./GenreChips/GenreChips";
import { HeroActions } from "./HeroActions/HeroActions";
import { HeroCreatorRow } from "./HeroCreatorRow/HeroCreatorRow";
import { HeroMetaRow } from "./HeroMetaRow/HeroMetaRow";
import { HeroCover } from "./HeroCover";
import { InProgressLine } from "./InProgressLine/InProgressLine";
import { RatingChip } from "./RatingChip/RatingChip";
import type { ScenarioBannerHeroProps } from "./ScenarioBannerHero.types";

export const ScenarioBannerHero: React.FC<ScenarioBannerHeroProps> = ({
  scenario,
  reviewCount,
  averageRating,
  inProgress,
  isOwner,
  isDraft,
  isBookmarked,
  isTogglingBookmark,
  isStartingPlaytest,
  actionsRef,
  onToggleBookmark,
  onShare,
  onPlaytest,
}) => (
  <section className="relative overflow-hidden rounded-md border border-border-subtle bg-surface lg:flex lg:min-h-[420px] lg:items-end">
    <HeroCover coverImageUrl={scenario.cover_image_url} />
    <RatingChip average={averageRating} reviewCount={reviewCount} />

    <div className="relative flex max-w-[720px] flex-col gap-4 p-4 sm:p-6 lg:p-10">
      <GenreChips genreTags={scenario.genre_tags} />
      <h1 className="line-clamp-3 font-display text-3xl font-extrabold leading-tight tracking-tight text-content md:text-5xl">
        {scenario.title}
      </h1>
      <HeroCreatorRow
        creatorId={scenario.creator_id}
        creatorDisplayName={scenario.creator_display_name}
        creatorAvatarUrl={scenario.creator_avatar_url}
        updatedAt={scenario.updated_at}
      />
      <HeroMetaRow
        scenario={scenario}
        reviewCount={reviewCount}
        averageRating={averageRating}
      />
      <div ref={actionsRef}>
        <HeroActions
          scenarioId={scenario.scenario_id}
          isOwner={isOwner}
          isDraft={isDraft}
          isBookmarked={isBookmarked}
          isTogglingBookmark={isTogglingBookmark}
          isStartingPlaytest={isStartingPlaytest}
          onToggleBookmark={onToggleBookmark}
          onShare={onShare}
          onPlaytest={onPlaytest}
        />
      </div>
      <InProgressLine scenarioId={scenario.scenario_id} summary={inProgress} />
    </div>
  </section>
);
