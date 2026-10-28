import React from "react";
import { StrategyDrawerTabs } from "./StrategyDrawerTabs";
import { StrategyDrawerPanel } from "./StrategyDrawerPanel";
import type { StrategyRightDrawerProps } from "./StrategyRightDrawer.types";

export const StrategyRightDrawer: React.FC<StrategyRightDrawerProps> = ({
  playthroughId,
  rivals = [],
  diplomacy,
  activeTab,
  isPinned,
  onSelectTab,
  onTogglePin,
  onJumpToRegion,
}) => {
  const isOpen = Boolean(activeTab || isPinned);

  return (
    <aside className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex items-center">
      <StrategyDrawerTabs
        activeTab={activeTab}
        rivalsCount={rivals.length}
        onSelectTab={onSelectTab}
      />
      <StrategyDrawerPanel
        playthroughId={playthroughId}
        isOpen={isOpen}
        isPinned={isPinned}
        activeTab={activeTab}
        rivals={rivals}
        diplomacy={diplomacy}
        onTogglePin={onTogglePin}
        onJumpToRegion={onJumpToRegion}
      />
    </aside>
  );
};
