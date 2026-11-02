import React from "react";
import { useStrategyArt } from "../../../hooks/useStrategyArt";
import { StrategyArtFrame } from "./StrategyArtFrame";
import type { StrategyArtSlotProps } from "./StrategyArtSlot.types";

export const StrategyArtSlot: React.FC<StrategyArtSlotProps> = ({
  playthroughId,
  kind,
  itemId,
  altText,
}) => {
  const { artUrl, isLoading, hasFailed, canRetry, retry } = useStrategyArt(playthroughId, kind, itemId);
  return (
    <StrategyArtFrame
      artUrl={artUrl}
      isLoading={isLoading}
      altText={altText}
      hasFailed={hasFailed}
      canRetry={canRetry}
      onRetry={retry}
    />
  );
};
