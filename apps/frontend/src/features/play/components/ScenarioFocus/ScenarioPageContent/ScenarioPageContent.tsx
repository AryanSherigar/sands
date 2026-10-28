import React, { useState } from "react";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import { useMaturePreference } from "@/shared/hooks/useMaturePreference";
import { useElementVisibility } from "../../../hooks/useElementVisibility";
import { useScenarioRuns } from "../../../hooks/useScenarioRuns";
import { useShareScenario } from "../../../hooks/useShareScenario";
import { useStartPlaytest } from "../../../hooks/useStartPlaytest";
import { useMatureRevealStore } from "../../../stores/matureReveal.store";
import {
  getPrimaryGenre,
  isMatureScenario,
} from "../../../utils/scenarioPage.utils";
import { DraftBanner } from "../DraftBanner/DraftBanner";
import { MatureGate } from "../MatureGate/MatureGate";
import { ScenarioAside } from "../ScenarioAside/ScenarioAside";
import { ScenarioBannerHero } from "../ScenarioBannerHero";
import { ScenarioContentColumn } from "../ScenarioContentColumn/ScenarioContentColumn";
import { StickyPlayBar } from "../StickyPlayBar/StickyPlayBar";
import type { ScenarioPageContentProps } from "./ScenarioPageContent.types";

export const ScenarioPageContent: React.FC<ScenarioPageContentProps> = ({
  scenario,
  focus,
}) => {
  const [playAnchor, setPlayAnchor] = useState<HTMLDivElement | null>(null);
  const isHeroPlayVisible = useElementVisibility(playAnchor);
  const { inProgress } = useScenarioRuns(scenario.scenario_id);
  const { startPlaytest, isStartingPlaytest } = useStartPlaytest(
    scenario.scenario_id,
    Boolean(scenario.setup_schema?.length),
  );
  const handleShare = useShareScenario(scenario.title);
  const { isEnabled: isMatureSaved } = useMaturePreference();
  const isRevealed = useMatureRevealStore((state) =>
    state.revealedScenarioIds.includes(scenario.scenario_id),
  );
  const reveal = useMatureRevealStore((state) => state.reveal);

  const isOwner = focus.currentUser?.user_id === scenario.creator_id;
  const isDraft = isOwner && scenario.status === "draft";
  const isGated =
    isMatureScenario(scenario) && !isOwner && !isMatureSaved && !isRevealed;

  return (
    <div
      className={`${getGenreAccentClass(getPrimaryGenre(scenario.genre_tags))} mx-auto max-w-[1200px] space-y-6 px-4 pb-40 pt-6 text-content md:px-10 lg:pb-24`}
    >
      {isDraft && <DraftBanner scenarioId={scenario.scenario_id} />}
      <ScenarioBannerHero
        scenario={scenario}
        reviewCount={focus.totalReviews}
        averageRating={focus.averageRating}
        inProgress={inProgress}
        isOwner={isOwner}
        isDraft={isDraft}
        isBookmarked={focus.isBookmarked}
        isTogglingBookmark={focus.isTogglingBookmark}
        isStartingPlaytest={isStartingPlaytest}
        actionsRef={setPlayAnchor}
        onToggleBookmark={focus.toggleBookmark}
        onShare={handleShare}
        onPlaytest={startPlaytest}
      />
      {isGated && (
        <MatureGate onShowAnyway={() => reveal(scenario.scenario_id)} />
      )}
      {!isGated && (
        <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[1fr_20rem]">
          <ScenarioContentColumn scenario={scenario} focus={focus} />
          <ScenarioAside
            scenario={scenario}
            focus={focus}
            inProgress={inProgress}
            isPlayCardVisible={!isHeroPlayVisible}
            isDraft={isDraft}
            isStartingPlaytest={isStartingPlaytest}
            onPlaytest={startPlaytest}
          />
        </div>
      )}
      {!isGated && !isHeroPlayVisible && (
        <StickyPlayBar
          scenarioId={scenario.scenario_id}
          isDraft={isDraft}
          isStartingPlaytest={isStartingPlaytest}
          onPlaytest={startPlaytest}
        />
      )}
    </div>
  );
};
