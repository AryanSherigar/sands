import React, { useEffect, useState } from "react";
import { MasterModeNav } from "./MasterModeNav";
import { MasterModeTabPanels } from "./MasterModeTabPanels";
import { StudioChatDrawer } from "./StudioChatDrawer";
import { TabHelpBanner } from "./TabHelpBanner";
import {
  MASTER_MODE_TABS,
  MasterModeStudioLayoutProps,
  MasterModeTab,
  MasterModeTabId,
} from "./MasterModeStudioLayout.types";
import { filterTabsByTools } from "./filterTabsByTools";
import { useScenario } from "../../hooks/useScenario";
import { useStudioStore } from "../../stores/studio.store";

const TOOLS_TAB_ID: MasterModeTabId = "tools";

export const MasterModeStudioLayout: React.FC<MasterModeStudioLayoutProps> = ({
  scenarioId,
}) => {
  const activeTab = useStudioStore((state) => state.activeMasterTab);
  const setActiveTab = useStudioStore((state) => state.setActiveMasterTab);
  const [visitedTabs, setVisitedTabs] = useState<Set<MasterModeTabId>>(
    () => new Set([activeTab]),
  );

  useEffect(() => {
    setVisitedTabs((prev) => {
      if (prev.has(activeTab)) return prev;
      const next = new Set(prev);
      next.add(activeTab);
      return next;
    });
  }, [activeTab]);

  const { scenario } = useScenario(scenarioId);
  const allTabs: readonly MasterModeTab[] = MASTER_MODE_TABS;
  const visibleTabs = filterTabsByTools(allTabs, scenario?.enabled_tools ?? []);
  const activeTabConfig = allTabs.find((tab) => tab.id === activeTab);
  const isActiveTabHidden =
    scenario !== null && !visibleTabs.some((tab) => tab.id === activeTab);

  useEffect(() => {
    if (isActiveTabHidden) setActiveTab(TOOLS_TAB_ID);
  }, [isActiveTabHidden, setActiveTab]);

  return (
    <div className="flex flex-1 overflow-hidden bg-surface-inset font-sans text-content-muted">
      <MasterModeNav
        scenarioId={scenarioId}
        tabs={visibleTabs}
        activeTab={activeTab}
        onTabSelect={setActiveTab}
      />
      <main className="flex-1 overflow-y-auto p-8">
        {activeTabConfig && (
          <TabHelpBanner key={activeTab} helpText={activeTabConfig.helpText} />
        )}
        <MasterModeTabPanels
          scenarioId={scenarioId}
          activeTab={activeTab}
          visitedTabs={visitedTabs}
        />
      </main>
      <StudioChatDrawer activeSection={activeTab} scenarioId={scenarioId} />
    </div>
  );
};
