import React from "react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { TabAddMenu } from "./TabAddMenu";
import type { TabLabelResolver } from "./StudioTabs.types";

export const MobileTabSwitcher: React.FC<{ getLabel: TabLabelResolver }> = ({ getLabel }) => {
  const openTabIds = useStudioTabsStore((state) => state.openTabIds);
  const focusTab = useStudioTabsStore((state) => state.focusTab);

  return (
    <div className="flex items-center gap-2 border-b border-border-subtle bg-surface-sunken px-3 py-2">
      <OverflowMenu
        label="Open tabs"
        triggerText={`${openTabIds.length} open`}
        items={openTabIds.map((tabId) => ({
          id: tabId,
          label: getLabel(tabId),
          onSelect: () => focusTab(tabId),
        }))}
      />
      <TabAddMenu />
    </div>
  );
};
