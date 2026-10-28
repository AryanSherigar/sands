import type {
  MyScenarioSummary,
  ScenarioStatusCounts,
  StudioTab,
} from "../../types/scenario.types";
import type { DisplayStatus } from "../../utils/scenarioRowStatus";

export interface ScenarioStatusBadgeProps {
  status: DisplayStatus;
}

export interface DraftProgressProps {
  scenario: MyScenarioSummary;
}

export interface ScenarioRowCoverProps {
  scenario: MyScenarioSummary;
}

export interface ScenarioRowMetaProps {
  scenario: MyScenarioSummary;
  status: DisplayStatus;
}

export interface ScenarioRowActionsProps {
  scenario: MyScenarioSummary;
  status: DisplayStatus;
  onDelete: (scenario: MyScenarioSummary) => void;
}

export interface ScenarioRowMenuProps {
  scenario: MyScenarioSummary;
  status: DisplayStatus;
  onDelete: (scenario: MyScenarioSummary) => void;
}

export interface StudioScenarioRowProps {
  scenario: MyScenarioSummary;
  onDelete: (scenario: MyScenarioSummary) => void;
}

export interface StudioFilterBarProps {
  tab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
  query: string;
  onQueryChange: (query: string) => void;
  counts: ScenarioStatusCounts | null;
}

export interface DeleteScenarioDialogProps {
  scenario: MyScenarioSummary | null;
  onClose: () => void;
  onConfirm: (scenario: MyScenarioSummary) => void;
}

export interface StudioEmptyStateProps {
  tab: StudioTab;
  query: string;
  hasAnyScenarios: boolean;
  onClearQuery: () => void;
  onNewScenario: () => void;
}

export interface ScenarioPublishedMetricsProps {
  scenario: MyScenarioSummary;
}

export interface ScenarioFailedPublishNoteProps {
  scenario: MyScenarioSummary;
}

export interface ScenarioRowSkeletonListProps {
  count: number;
}
