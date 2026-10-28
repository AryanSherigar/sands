import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { ScenarioResponse } from "../../types/scenario.types";
import type { PublishReport, StrategyFields } from "../../types/strategyDocument.types";

export type EditStrategyFields = (change: (current: StrategyFields) => StrategyFields) => void;

export interface StrategyTitleFieldProps {
  scenario: ScenarioResponse;
}

export interface StrategyMapSectionProps {
  scenarioId: string;
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
  onFlush: () => Promise<void>;
}
