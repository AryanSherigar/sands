import type { ReactZoomPanPinchRef } from "react-zoom-pan-pinch";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import type { CampaignWorldView } from "../../../types/simulation.types";
import type { SelectedEntity, StrategyMapMode } from "../../../stores/strategyPlay.types";
import type { ActiveSituation } from "../../../types/situation.types";

export interface StrategyMapCanvasProps {
  document: MapDocument;
  world?: CampaignWorldView;
  selectedEntity?: SelectedEntity | null;
  onSelectEntity: (entity: SelectedEntity | null) => void;
  situations?: ActiveSituation[];
  onSelectSituation?: (situationId: string, regionId: string) => void;
  activeMapMode?: StrategyMapMode;
  groupArmyIds?: string[];
  onToggleGroupArmy?: (armyId: string) => void;
}

export interface SettlementPinProps {
  name: string;
  regionId: string;
  coords: { x: number; y: number };
  isSelected?: boolean;
  onClick: (regionId: string) => void;
}

export interface ArmyBannerPinProps {
  armyId: string;
  commanderName?: string | null;
  troopCount: number;
  coords: { x: number; y: number };
  isHostile?: boolean;
  isSelected?: boolean;
  isGrouped?: boolean;
  onClick: (armyId: string, isAdditive: boolean) => void;
}

export interface CrisisAlertPinProps {
  coords: { x: number; y: number };
  label: string;
}

export interface StrategyMapViewportProps extends StrategyMapCanvasProps {
  onControlsReady?: (ref: ReactZoomPanPinchRef) => void;
}
