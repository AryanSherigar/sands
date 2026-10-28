import type { QueuedOrderView } from "../../../types/simulation.types";

export interface StrategyOrdersTrayProps {
  orders: QueuedOrderView[];
  ordersRemaining?: number;
  ordersTotal?: number;
  regionNames?: Record<string, string>;
  onCancelOrder: (commandId: string) => void;
}

export interface StrategyEndTurnModuleProps {
  ordersRemaining: number;
  nextSeason?: string;
  isLoading?: boolean;
  isDisabled?: boolean;
  onEndTurn: () => void;
}

export interface StrategyNoticeBannerProps {
  message: string;
  onDismiss?: () => void;
}
