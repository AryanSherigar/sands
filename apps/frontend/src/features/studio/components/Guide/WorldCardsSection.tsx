import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { getQuestionGroupsForCard } from "../../constants/guideQuestions";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useOpenCardTab } from "../../hooks/useOpenCardTab";
import { getCardKind } from "../../lib/cardKind";
import type { CardKind } from "../../types/card.types";
import { Card } from "../Card/Card";

const ADD_BUTTONS: Array<{ kind: CardKind; label: string }> = [
  { kind: "place", label: "+ Place" },
  { kind: "group", label: "+ Group" },
  { kind: "thing", label: "+ Thing" },
  { kind: "other", label: "+ Other" },
];

export const WorldCardsSection: React.FC = () => {
  const { scenarioId, addCard } = useGuide();
  const { cards, getTypeLabel } = useGuideCards();
  const { addLine } = useAlwaysRemember();
  const openCardTab = useOpenCardTab();
  const worldCards = [...cards.places, ...cards.groups, ...cards.things, ...cards.others];

  return (
    <section aria-labelledby="world-cards" className="space-y-3">
      <div className="space-y-1">
        <h3 id="world-cards" className="text-heading font-semibold text-content">
          Places, groups and things
        </h3>
        <p className="text-meta text-content-muted">
          These come into the story when they're mentioned, using their triggers.
        </p>
      </div>
      <div className="space-y-4">
        {scenarioId &&
          worldCards.map((entity) => (
            <Card
              key={entity.entity_id}
              scenarioId={scenarioId}
              entityId={entity.entity_id}
              questions={getQuestionGroupsForCard(getCardKind(entity.entity_type), false)}
              typeLabel={getTypeLabel(entity)}
              onOpenCard={openCardTab}
              onAddToAlwaysRemember={addLine}
            />
          ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {ADD_BUTTONS.map((button) => (
          <Button
            key={button.kind}
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => addCard(button.kind)}
          >
            {button.label}
          </Button>
        ))}
      </div>
    </section>
  );
};
