import React from "react";
import { StrategyDrawerTabs } from "./StrategyDrawerTabs";
import { StrategyDrawerPanel } from "./StrategyDrawerPanel";
import type { StrategyRightDrawerProps } from "./StrategyRightDrawer.types";

export const StrategyRightDrawer: React.FC<StrategyRightDrawerProps> = (props) => {
  const { rivals = [], activeTab, isPinned, onSelectTab, world, ...panelProps } = props;
  const isOpen = Boolean(activeTab || isPinned);
  const obligationsCount =
    (world?.pending_calls?.length ?? 0) + (world?.pending_demands?.length ?? 0);

  return (
    <aside className="fixed right-0 top-1/2 -translate-y-1/2 z-40 flex items-center">
      <StrategyDrawerTabs
        activeTab={activeTab}
        rivalsCount={rivals.length}
        obligationsCount={obligationsCount}
        onSelectTab={onSelectTab}
      />
      <StrategyDrawerPanel
        {...panelProps}
        world={world}
        activeTab={activeTab}
        isPinned={isPinned}
        isOpen={isOpen}
        rivals={rivals}
      />
    </aside>
  );
};
