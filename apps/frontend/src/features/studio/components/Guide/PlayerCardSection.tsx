import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { PLAYER_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useOpenCardTab } from "../../hooks/useOpenCardTab";
import { Card } from "../Card/Card";

const PLAYER_CARD_NAME = "The player";

export const PlayerCardSection: React.FC = () => {
  const { scenarioId, addCard } = useGuide();
  const { cards, getTypeLabel } = useGuideCards();
  const { addLine } = useAlwaysRemember();
  const openCardTab = useOpenCardTab();
  const player = cards.player;

  const handleDescribe = (): void =>
    addCard("character", { name: PLAYER_CARD_NAME, isPlayer: true });

  return (
    <section aria-labelledby="about-the-player" className="space-y-3">
      <h3 id="about-the-player" className="text-heading font-semibold text-content">
        About the player
      </h3>
      {player && scenarioId ? (
        <Card
          scenarioId={scenarioId}
          entityId={player.entity_id}
          questions={PLAYER_QUESTION_GROUPS}
          typeLabel={getTypeLabel(player)}
          onOpenCard={openCardTab}
          onAddToAlwaysRemember={addLine}
        />
      ) : (
        <Button type="button" variant="secondary" onClick={handleDescribe}>
          Describe the player
        </Button>
      )}
    </section>
  );
};
