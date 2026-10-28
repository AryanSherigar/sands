import React from "react";
import { IconPlus } from "@tabler/icons-react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import { useGuide } from "../../hooks/useGuide";
import type { CardKind } from "../../types/card.types";

const NEW_ITEMS: Array<{ kind: CardKind; label: string }> = [
  { kind: "character", label: "New character" },
  { kind: "place", label: "New place" },
  { kind: "group", label: "New group" },
  { kind: "thing", label: "New thing" },
  { kind: "other", label: "New other" },
];

export const TabAddMenu: React.FC = () => {
  const { addCard } = useGuide();

  return (
    <OverflowMenu
      label="New tab"
      icon={<IconPlus size={16} aria-hidden="true" />}
      items={NEW_ITEMS.map((item) => ({
        id: item.kind,
        label: item.label,
        onSelect: () => addCard(item.kind, { shouldOpenTab: true }),
      }))}
    />
  );
};
