import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { ScenarioResponse } from "../../types/scenario.types";
import type { StartPanelId } from "../../lib/strategyPanels";
import type { PublishIssue, PublishReport, StrategyArmy, StrategyCommander, StrategyFaction, StrategyFields, StrategyGrudge, StrategyRelation } from "../../types/strategyDocument.types";

export type EditStrategyFields = (change: (current: StrategyFields) => StrategyFields) => void;

export interface StrategyTitleFieldProps {
  scenario: ScenarioResponse;
}

export interface StrategyMapSectionProps {
  scenarioId: string;
}

export interface MapGenerationStatusProps {
  scenarioId: string;
  hasSavedMap: boolean;
}

export interface StrategyFactionsSectionProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyFactionCardProps {
  factionId: string;
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyStartSectionProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyPublishSectionProps {
  scenario: ScenarioResponse;
  report: PublishReport | undefined;
  isMapMissing: boolean;
  onFlush: () => Promise<boolean>;
  onRecheck: () => Promise<PublishReport | undefined>;
  onOpenPanel: (panelId: StartPanelId) => void;
}

export interface StrategyNumberFieldProps {
  label: string;
  value: number;
  max?: number;
  onCommit: (value: number) => void;
}

export interface StrategyFactionStatsProps {
  faction: StrategyFaction;
  onEdit: EditStrategyFields;
}

export interface StrategyRegionEconomyProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyArmiesPanelProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyCommanderFieldsProps {
  army: StrategyArmy;
  commander: StrategyCommander | null;
  onEdit: EditStrategyFields;
}

export interface StrategyArmyRowProps {
  army: StrategyArmy;
  commander: StrategyCommander | null;
  regions: MapRegion[];
  isForeign: boolean;
  onEdit: EditStrategyFields;
}

export interface StrategyRelationsPanelProps {
  fields: StrategyFields;
  onEdit: EditStrategyFields;
}

export interface StrategyRelationRowProps {
  factionA: StrategyFaction;
  factionB: StrategyFaction;
  relation: StrategyRelation | undefined;
  onEdit: EditStrategyFields;
}

export interface StrategyClaimsEditorProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyGrudgesEditorProps {
  fields: StrategyFields;
  onEdit: EditStrategyFields;
}

export interface StrategyClaimsGrudgesPanelProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyGrudgeRowProps {
  grudge: StrategyGrudge;
  holderName: string;
  targetName: string;
  onEdit: EditStrategyFields;
}

export interface StrategyTimelinePanelProps {
  fields: StrategyFields;
  onEdit: EditStrategyFields;
}

export type StrategyRulesPanelProps = StrategyTimelinePanelProps;

export interface StrategyPresetPickerProps {
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyIssueListProps {
  issues: PublishIssue[];
  tone: string;
  onOpenPanel: (panelId: StartPanelId) => void;
}

export interface StrategyStartPanelBodyProps {
  panelId: StartPanelId;
  fields: StrategyFields;
  regions: MapRegion[];
  onEdit: EditStrategyFields;
}

export interface StrategyStartSituationProps {
  fields: StrategyFields;
  regions: MapRegion[];
  openPanel: StartPanelId | null;
  onOpenPanel: (panelId: StartPanelId | null) => void;
  onEdit: EditStrategyFields;
}

export interface StrategyChatPanelProps {
  scenarioId: string;
  title: string;
  fields: StrategyFields;
  mapRegions: MapRegion[];
  activePanel: string | null;
  edit: EditStrategyFields;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}
