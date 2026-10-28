import type { Icon } from "@tabler/icons-react";

export interface MobileTabItemProps {
  label: string;
  Icon: Icon;
  isActive: boolean;
  to?: string;
  onSelect?: () => void;
}
