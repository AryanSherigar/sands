import React from "react";
import { getGuideStep } from "../../lib/guideSteps";
import { FeatureAnchor } from "../NewFeatures/FeatureAnchor";
import { GuideStepLayout } from "./GuideStepLayout";
import { OpeningSection } from "./OpeningSection";
import { StorytellingStyleSection } from "./StorytellingStyleSection";

export const StepOpening: React.FC = () => (
  <GuideStepLayout step={getGuideStep("opening")}>
    <OpeningSection />
    <FeatureAnchor featureId="storytelling-style">
      <StorytellingStyleSection />
    </FeatureAnchor>
  </GuideStepLayout>
);
