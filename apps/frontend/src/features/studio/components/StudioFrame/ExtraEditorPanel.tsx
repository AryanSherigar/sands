import React from "react";
import { Button } from "@/shared/components/ui/Button";
import {
  EXTRA_BACK_LABEL,
  formatExtraNeedsAdvanced,
  type ExtraId,
} from "../../constants/extras";
import { ADVANCED_MODE_ON } from "../../constants/advancedMode";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { useGoToGuideStep } from "../../hooks/useGoToGuideStep";
import { useGuide } from "../../hooks/useGuide";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { AtmosphereEditor } from "../AtmosphereEditor/AtmosphereEditor";
import { MapEditor } from "../MapEditor/MapEditor";
import { MinigameEditor } from "../MinigameEditor/MinigameEditor";
import { MusicSlotEditor } from "../MusicSlotEditor/MusicSlotEditor";
import { RuleCheckEditor } from "../RuleCheckEditor/RuleCheckEditor";
import { SheetRuleEditor } from "../SheetRuleEditor/SheetRuleEditor";
import type { ExtraEditorPanelProps, ExtraEditorProps } from "./StudioFrame.types";

const EDITORS: Record<ExtraId, React.ComponentType<ExtraEditorProps>> = {
  map: MapEditor,
  music: MusicSlotEditor,
  minigames: MinigameEditor,
  atmosphere: AtmosphereEditor,
  rule_sheet: SheetRuleEditor,
  rule_checks: RuleCheckEditor,
};

export const ExtraEditorPanel: React.FC<ExtraEditorPanelProps> = ({ extra }) => {
  const { scenarioId, scenario } = useGuide();
  const goToStep = useGoToGuideStep();
  const openTab = useStudioTabsStore((state) => state.openTab);
  const Editor = EDITORS[extra.id];

  if (!scenarioId || !scenario) return null;
  const handleBack = (): void => {
    goToStep("extras");
    openTab(GUIDE_TAB_ID);
  };

  return (
    <div className="mx-auto w-full max-w-[960px] space-y-4 px-4 py-8">
      <Button type="button" variant="ghost" size="sm" onClick={handleBack}>
        ← {EXTRA_BACK_LABEL}
      </Button>
      {scenario.mode === ADVANCED_MODE_ON ? (
        <Editor scenarioId={scenarioId} canEnableComposure />
      ) : (
        <p role="status" className="text-body text-content-muted">
          {formatExtraNeedsAdvanced(extra.name)}
        </p>
      )}
    </div>
  );
};
