import type { ReactNode } from "react";
import type { GuideStepStatus } from "../../lib/guideProgress";

export interface YourStoryGroupProps {
  label: string;
  count: number;
  addLabel?: string;
  onAdd?: () => void;
  children: ReactNode;
}

export interface QuickFilterProps {
  value: string;
  onChange: (next: string) => void;
}

export interface GuideStepItemsProps {
  filterText: string;
}

export interface AdvancedRailItemsProps {
  filterText: string;
}

export interface CollapsedStepsProps {
  isAdvanced: boolean;
}

export interface StatusIconProps {
  status: GuideStepStatus;
}
