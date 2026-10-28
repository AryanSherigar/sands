import React from "react";
import { AppShell } from "@/shared/components/layout/AppShell";
import { useGuide } from "../../hooks/useGuide";
import { usePruneMissingCardTabs } from "../../hooks/usePruneMissingCardTabs";
import { useResumeGuide } from "../../hooks/useResumeGuide";
import { useSyncFeatureHints } from "../../hooks/useSyncFeatureHints";
import { useStudioTabsPersistence } from "../../hooks/useStudioTabsPersistence";
import { GuideScenarioProvider } from "../Guide/GuideScenarioProvider";
import { StudioTabs } from "../StudioTabs/StudioTabs";
import { YourStoryList } from "../YourStoryList/YourStoryList";
import { StudioPanels } from "./StudioPanels";
import { StudioTopBar } from "./StudioTopBar";
import type { StudioFrameProps } from "./StudioFrame.types";

const StudioFrameBody: React.FC = () => {
  const { scenarioId, scenario } = useGuide();
  useStudioTabsPersistence(scenarioId);
  usePruneMissingCardTabs();
  useSyncFeatureHints();
  useResumeGuide();
  const isPublishing = scenario?.status === "publishing";

  return (
    <div className="flex min-h-[100dvh] h-dvh flex-col overflow-hidden bg-surface-sunken font-sans text-content">
      <StudioTopBar />
      <main className="flex min-h-0 flex-1 flex-col">
        <AppShell nav={<YourStoryList />} showFloatingNav={false}>
          <StudioTabs />
          <fieldset
            disabled={isPublishing}
            className="m-0 flex min-h-0 min-w-0 flex-1 flex-col border-0 p-0"
          >
            <StudioPanels />
          </fieldset>
        </AppShell>
      </main>
    </div>
  );
};

export const StudioFrame: React.FC<StudioFrameProps> = ({ scenarioId, onDraftCreated }) => (
  <GuideScenarioProvider scenarioId={scenarioId} onDraftCreated={onDraftCreated}>
    <StudioFrameBody />
  </GuideScenarioProvider>
);
