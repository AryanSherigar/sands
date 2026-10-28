import React from "react";
import { getGuideStep } from "../../lib/guideSteps";
import { FeatureAnchor } from "../NewFeatures/FeatureAnchor";
import { GuideStepLayout } from "./GuideStepLayout";
import { PlayerCardSection } from "./PlayerCardSection";
import { PlayerModeChoice } from "./PlayerModeChoice";
import { SetupFieldsSection } from "./SetupFieldsSection";

export const StepPlayer: React.FC = () => (
  <GuideStepLayout step={getGuideStep("player")}>
    <FeatureAnchor featureId="player-step">
      <PlayerModeChoice />
    </FeatureAnchor>
    <PlayerCardSection />
    <SetupFieldsSection />
  </GuideStepLayout>
);
