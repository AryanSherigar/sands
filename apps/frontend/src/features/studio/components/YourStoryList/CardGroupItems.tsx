import React from "react";
import { IconCards } from "@tabler/icons-react";
import { SidebarButton } from "@/shared/components/layout/SidebarButton";
import { useGuide } from "../../hooks/useGuide";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { filterByName } from "../../lib/cardGroups";
import { buildCardTabId } from "../../lib/studioTabs";
import type { CardKind } from "../../types/card.types";
import type { EntityResponse } from "../../types/entity.types";
import { YourStoryGroup } from "./YourStoryGroup";

interface CardGroupItemsProps {
  label: string;
  kind: CardKind;
  entities: EntityResponse[];
  filterText: string;
}

export const CardGroupItems: React.FC<CardGroupItemsProps> = ({
  label,
  kind,
  entities,
  filterText,
}) => {
  const { addCard } = useGuide();
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const openTab = useStudioTabsStore((state) => state.openTab);
  const visible = filterByName(entities, filterText);
  if (filterText.trim() && visible.length === 0) return null;

  return (
    <YourStoryGroup
      label={label}
      count={entities.length}
      addLabel={`Add to ${label}`}
      onAdd={() => addCard(kind, { shouldOpenTab: true })}
    >
      {visible.map((entity) => {
        const tabId = buildCardTabId(entity.entity_id);
        return (
          <SidebarButton
            key={entity.entity_id}
            icon={<IconCards size={16} aria-hidden="true" />}
            label={entity.canonical_name || "Untitled"}
            isActive={activeTabId === tabId}
            onClick={() => openTab(tabId)}
          />
        );
      })}
    </YourStoryGroup>
  );
};
