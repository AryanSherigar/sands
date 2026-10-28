import type { StrategyInspectorAction } from "../../../types/strategyActions.types";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { ArmyView, CampaignWorldView } from "../../../types/simulation.types";
import type { SelectedEntity } from "../../../stores/strategyPlay.types";

export interface StrategyLeftInspectorProps {
  selectedEntity: SelectedEntity | null;
  region?: MapRegion | null;
  army?: ArmyView | null;
  world?: CampaignWorldView;
  onClose: () => void;
  onAction?: (action: StrategyInspectorAction) => void;
}

export type { ProvinceCharterViewProps } from "./ProvinceCharterView.types";
export type { ArmyRosterViewProps } from "./ArmyRosterView.types";
