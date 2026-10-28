import React, { useState } from "react";
import { IconCircle } from "@tabler/icons-react";
import { SidebarButton } from "@/shared/components/layout/SidebarButton";
import { useAppSidebar } from "@/shared/components/layout/appSidebarContext";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { getGuideSteps } from "../../lib/guideStepsFor";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { AdvancedModeRow } from "./AdvancedModeRow";
import { AdvancedRailItems } from "./AdvancedRailItems";
import { CardGroupItems } from "./CardGroupItems";
import { GuideStepItems } from "./GuideStepItems";
import { NewFeaturesSection } from "./NewFeaturesSection";
import { QuickFilter } from "./QuickFilter";
import { StoryMenu } from "./StoryMenu";
import type { CollapsedStepsProps } from "./YourStoryList.types";

const CollapsedSteps: React.FC<CollapsedStepsProps> = ({ isAdvanced }) => {
  const guideStep = useStudioTabsStore((state) => state.guideStep);
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);
  const openTab = useStudioTabsStore((state) => state.openTab);

  return (
    <>
      {getGuideSteps(isAdvanced).map((step) => (
        <SidebarButton
          key={step.id}
          icon={<IconCircle size={14} aria-hidden="true" />}
          label={`${step.number}. ${step.name}`}
          isActive={guideStep === step.number}
          onClick={() => {
            openTab(GUIDE_TAB_ID);
            setGuideStep(step.number);
          }}
        />
      ))}
    </>
  );
};

export const YourStoryList: React.FC = () => {
  const { collapsed } = useAppSidebar();
  const { scenario } = useGuide();
  const isAdvanced = scenario?.mode === "master";
  const [filterText, setFilterText] = useState("");
  const { cards } = useGuideCards();

  if (collapsed) return <CollapsedSteps isAdvanced={isAdvanced} />;

  return (
    <div className="flex min-h-full flex-col gap-3">
      <QuickFilter value={filterText} onChange={setFilterText} />
      <GuideStepItems filterText={filterText} />
      {isAdvanced && <AdvancedRailItems filterText={filterText} />}
      <CardGroupItems label="Characters" kind="character" entities={cards.characters} filterText={filterText} />
      <CardGroupItems label="Places" kind="place" entities={cards.places} filterText={filterText} />
      <CardGroupItems label="Groups" kind="group" entities={cards.groups} filterText={filterText} />
      <CardGroupItems label="Things" kind="thing" entities={cards.things} filterText={filterText} />
      <CardGroupItems label="Other" kind="other" entities={cards.others} filterText={filterText} />
      <NewFeaturesSection />
      <div className="mt-auto space-y-2 border-t border-border-subtle pt-3">
        <AdvancedModeRow />
        <div className="flex justify-end px-1">
          <StoryMenu />
        </div>
      </div>
    </div>
  );
};
