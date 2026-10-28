import React from "react";
import { WORLD_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { WORLD_LORE_DOCUMENT_KEY } from "../../constants/worldDocumentKeys";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useWorldDocument } from "../../hooks/useWorldDocument";
import { getGuideStep } from "../../lib/guideSteps";
import { LoreBox } from "../LoreBox/LoreBox";
import { FeatureAnchor } from "../NewFeatures/FeatureAnchor";
import { AlwaysRememberList } from "./AlwaysRememberList";
import { GuideStepLayout } from "./GuideStepLayout";
import { WorldCardsSection } from "./WorldCardsSection";

export const StepWorld: React.FC = () => {
  const worldLore = useWorldDocument(WORLD_LORE_DOCUMENT_KEY);
  const { addLine } = useAlwaysRemember();

  return (
    <GuideStepLayout step={getGuideStep("world")}>
      <LoreBox
        document={worldLore.document}
        onChange={worldLore.onChange}
        questions={WORLD_QUESTION_GROUPS}
        ariaLabel="Your world"
        placeholder="Describe the place, the people and what makes it feel real."
        onAddToAlwaysRemember={addLine}
      />
      <FeatureAnchor featureId="always-remember">
        <AlwaysRememberList />
      </FeatureAnchor>
      <WorldCardsSection />
    </GuideStepLayout>
  );
};
