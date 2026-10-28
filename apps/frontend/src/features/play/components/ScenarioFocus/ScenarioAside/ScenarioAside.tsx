import React from "react";
import { AuthorDossier } from "../AuthorDossier/AuthorDossier";
import { PlayCard } from "../PlayCard/PlayCard";
import { QuickSpecs } from "../QuickSpecs/QuickSpecs";
import { ScenarioPublicPlaythroughs } from "../ScenarioPublicPlaythroughs";
import type { ScenarioAsideProps } from "./ScenarioAside.types";

export const ScenarioAside: React.FC<ScenarioAsideProps> = ({
  scenario,
  focus,
  inProgress,
  isPlayCardVisible,
  isDraft,
  isStartingPlaytest,
  onPlaytest,
}) => (
  <aside className="space-y-4 lg:sticky lg:top-24">
    {isPlayCardVisible && (
      <div className="hidden lg:block">
        <PlayCard
          scenarioId={scenario.scenario_id}
          isDraft={isDraft}
          isStartingPlaytest={isStartingPlaytest}
          onPlaytest={onPlaytest}
          title={scenario.title}
          playCount={scenario.play_count}
          inProgress={inProgress}
        />
      </div>
    )}
    <QuickSpecs
      estimatedPlaytime={scenario.estimated_playtime}
      mode={scenario.mode}
      complexityTier={scenario.complexity_tier}
    />
    <ScenarioPublicPlaythroughs
      playthroughs={focus.publicPlaythroughs}
      isError={focus.isPlaythroughsError}
      onRetry={focus.refetchPlaythroughs}
    />
    <AuthorDossier
      creatorId={scenario.creator_id}
      displayName={scenario.creator_display_name}
      avatarUrl={scenario.creator_avatar_url}
      bio={scenario.creator_bio}
      otherScenariosCount={scenario.creator_other_scenarios_count ?? 0}
    />
  </aside>
);
