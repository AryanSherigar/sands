import React from "react";
import { PREMISE_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { PREMISE_WORD_GUIDE } from "../../constants/guideLimits";
import { PREMISE_DOCUMENT_KEY } from "../../constants/worldDocumentKeys";
import { useGuide } from "../../hooks/useGuide";
import { useWorldDocument } from "../../hooks/useWorldDocument";
import { getGuideStep } from "../../lib/guideSteps";
import { LoreBox } from "../LoreBox/LoreBox";
import { GenreChips } from "./GenreChips";
import { GuideStepLayout } from "./GuideStepLayout";
import { MoodChips } from "./MoodChips";

export const StepPremise: React.FC = () => {
  const { scenario } = useGuide();
  const premise = useWorldDocument(PREMISE_DOCUMENT_KEY);
  const logline = scenario?.logline?.trim() ?? "";

  return (
    <GuideStepLayout step={getGuideStep("premise")}>
      {logline && (
        <p className="text-meta text-content-muted">
          Your idea · Saved: “{logline}”
        </p>
      )}
      <LoreBox
        document={premise.document}
        onChange={premise.onChange}
        softWordGuide={PREMISE_WORD_GUIDE}
        questions={PREMISE_QUESTION_GROUPS}
        ariaLabel="Your story and the stakes"
        placeholder="Who is at the centre of it, what do they want, and what could go wrong?"
      />
      <GenreChips />
      <MoodChips />
    </GuideStepLayout>
  );
};
