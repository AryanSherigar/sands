import React from "react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";
import { CARD_DEFAULT_NAME_LABEL } from "../../constants/card";
import type { CardMenuProps } from "./Card.types";

export const CardMenu: React.FC<CardMenuProps> = ({
  name,
  onOpenInTab,
  onDuplicate,
  onDelete,
}) => {
  const items: OverflowMenuItem[] = [];
  if (onOpenInTab) {
    items.push({ id: "open", label: "Open in tab", onSelect: onOpenInTab });
  }
  items.push({ id: "duplicate", label: "Duplicate", onSelect: onDuplicate });
  items.push({ id: "delete", label: "Delete", isDanger: true, onSelect: onDelete });

  return (
    <OverflowMenu
      label={`${name.trim() || CARD_DEFAULT_NAME_LABEL} options`}
      items={items}
    />
  );
};
