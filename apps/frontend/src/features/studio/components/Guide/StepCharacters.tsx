import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useOpenCardTab } from "../../hooks/useOpenCardTab";
import { getGuideStep } from "../../lib/guideSteps";
import { CHARACTER_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { Card } from "../Card/Card";
import { GuideStepLayout } from "./GuideStepLayout";

export const StepCharacters: React.FC = () => {
  const { scenarioId, addCard } = useGuide();
  const { cards } = useGuideCards();
  const { addLine } = useAlwaysRemember();
  const openCardTab = useOpenCardTab();

  return (
    <GuideStepLayout step={getGuideStep("characters")}>
      <div className="space-y-4">
        {scenarioId &&
          cards.characters.map((character) => (
            <Card
              key={character.entity_id}
              scenarioId={scenarioId}
              entityId={character.entity_id}
              questions={CHARACTER_QUESTION_GROUPS}
              onOpenCard={openCardTab}
              onAddToAlwaysRemember={addLine}
            />
          ))}
        <Button type="button" variant="secondary" onClick={() => addCard("character")}>
          + Add character
        </Button>
      </div>
    </GuideStepLayout>
  );
};
