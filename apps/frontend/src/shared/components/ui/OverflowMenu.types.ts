import type React from "react";

export interface OverflowMenuItem {
  id: string;
  label: string;
  onSelect: () => void;
  isDanger?: boolean;
}

export interface OverflowMenuProps {
  label: string;
  items: OverflowMenuItem[];
  icon?: React.ReactNode;
  triggerText?: string;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
}
