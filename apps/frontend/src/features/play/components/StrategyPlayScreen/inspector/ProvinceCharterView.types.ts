import type { StrategyInspectorAction } from "../../../types/strategyActions.types";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type { CampaignWorldView } from "../../../types/simulation.types";

export interface ProvinceCharterViewProps {
  region: MapRegion;
  world?: CampaignWorldView;
  onAction?: (action: StrategyInspectorAction) => void;
}
