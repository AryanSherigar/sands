import React, { useState } from "react";
import { MAKE_PUBLIC_FAILED_MESSAGE } from "../../constants/finish";
import { useGuide } from "../../hooks/useGuide";
import { useOpenPlaytestTab } from "../../hooks/useOpenPlaytestTab";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useStoryPublish } from "../../hooks/useStoryPublish";
import {
  describeMissingRequired,
  getRequiredItems,
  getSuggestions,
} from "../../lib/finishChecklist";
import { getGuideStep } from "../../lib/guideSteps";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { PublishSuccess } from "../PublishSuccess/PublishSuccess";
import { ContentWarningsSection } from "./ContentWarningsSection";
import { FinishActions } from "./FinishActions";
import { FinishChecklist } from "./FinishChecklist";
import { FinishCoverSection } from "./FinishCoverSection";
import { FinishPreviewCard } from "./FinishPreviewCard";
import { GuideStepLayout } from "./GuideStepLayout";
import { VisibilityChoice } from "./VisibilityChoice";

export const StepFinish: React.FC = () => {
  const { scenarioId, scenario, saveFields, flushSaves } = useGuide();
  const { cards } = useGuideCards();
  const publishFlow = useStoryPublish();
  const [isMakingPublic, setIsMakingPublic] = useState(false);
  const [makePublicError, setMakePublicError] = useState<string | null>(null);
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);
  const handlePlaytest = useOpenPlaytestTab();
  const step = getGuideStep("finish");

  const requiredItems = getRequiredItems(scenario);
  const suggestions = getSuggestions(scenario, cards.characters.length);
  const missingMessage = describeMissingRequired(requiredItems);

  const handleMakePublic = async (): Promise<void> => {
    setIsMakingPublic(true);
    setMakePublicError(null);
    saveFields({ visibility: "public" });
    try {
      await flushSaves();
    } catch {
      setMakePublicError(MAKE_PUBLIC_FAILED_MESSAGE);
    } finally {
      setIsMakingPublic(false);
    }
  };
  const handlePublish = (): void => void publishFlow.publish();

  if (publishFlow.hasJustPublished && scenarioId) {
    return (
      <GuideStepLayout step={step} shouldShowExample={false}>
        <PublishSuccess
          scenarioId={scenarioId}
          isPublic={scenario?.visibility === "public"}
          achievement={publishFlow.achievement}
          isMakingPublic={isMakingPublic}
          makePublicError={makePublicError}
          onMakePublic={() => void handleMakePublic()}
        />
      </GuideStepLayout>
    );
  }

  return (
    <GuideStepLayout step={step} shouldShowExample={false}>
      <FinishPreviewCard
        title={scenario?.title ?? ""}
        logline={scenario?.logline ?? null}
        coverImageUrl={scenario?.cover_image_url ?? null}
        primaryGenre={scenario?.genre_tags[0] ?? null}
      />
      <FinishCoverSection />
      <VisibilityChoice />
      <ContentWarningsSection />
      <FinishChecklist requiredItems={requiredItems} suggestions={suggestions} onFix={setGuideStep} />
      <FinishActions
        isPublishDisabled={Boolean(missingMessage) || publishFlow.isBusy || !scenarioId}
        isBusy={publishFlow.isBusy}
        isLive={scenario?.status === "published"}
        missingMessage={missingMessage}
        failureMessage={publishFlow.failureMessage}
        onPlaytest={handlePlaytest}
        onPublish={handlePublish}
      />
    </GuideStepLayout>
  );
};
