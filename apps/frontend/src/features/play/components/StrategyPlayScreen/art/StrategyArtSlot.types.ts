import type { StrategyArtKind } from "../../../types/strategyArt.types";

export interface StrategyArtSlotProps {
  playthroughId?: string;
  kind: StrategyArtKind;
  itemId?: string;
  altText: string;
}
