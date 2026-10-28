import React from "react";
import { getQuestionGroupsForCard } from "../../constants/guideQuestions";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useOpenCardTab } from "../../hooks/useOpenCardTab";
import { getCardKind } from "../../lib/cardKind";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildCardTabId } from "../../lib/studioTabs";
import { Card } from "../Card/Card";

export const CardTabPanel: React.FC<{ entityId: string }> = ({ entityId }) => {
  const { scenarioId } = useGuide();
  const { entities, isLoading, getTypeLabel } = useGuideCards();
  const { addLine } = useAlwaysRemember();
  const openCardTab = useOpenCardTab();
  const closeTab = useStudioTabsStore((state) => state.closeTab);
  const entity = entities.find((candidate) => candidate.entity_id === entityId);

  if (!scenarioId || (isLoading && !entity)) return null;
  if (!entity) {
    return <p className="p-8 text-meta text-content-muted">This card no longer exists.</p>;
  }

  return (
    <div className="mx-auto w-full max-w-[640px] px-4 py-8">
      <Card
        scenarioId={scenarioId}
        entityId={entityId}
        questions={getQuestionGroupsForCard(getCardKind(entity.entity_type), Boolean(entity.is_player))}
        typeLabel={getTypeLabel(entity)}
        onOpenCard={openCardTab}
        onDeleted={(deletedId) => closeTab(buildCardTabId(deletedId))}
        onAddToAlwaysRemember={addLine}
      />
    </div>
  );
};
