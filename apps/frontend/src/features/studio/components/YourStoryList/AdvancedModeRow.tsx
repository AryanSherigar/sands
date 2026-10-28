import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { ADVANCED_NARROW_NOTICE } from "../../constants/advancedMode";
import { PUBLISHING_NOTICE } from "../../constants/studioFrame";
import { useAdvancedMode } from "../../hooks/useAdvancedMode";
import { useGuide } from "../../hooks/useGuide";
import { getRequiredItems } from "../../lib/finishChecklist";
import { TurnOffDialog } from "../AdvancedModeSwitch/TurnOffDialog";

export const AdvancedModeRow: React.FC = () => {
  const { isAdvanced, canUseAdvanced, isPublishing, isSwitching, turnOn, turnOff } =
    useAdvancedMode();
  const { scenario } = useGuide();
  const missingPublishItems = getRequiredItems(scenario)
    .filter((item) => !item.isDone)
    .map((item) => item.label.toLowerCase());
  const [isConfirmingOff, setIsConfirmingOff] = useState(false);

  const handleConfirmOff = async (): Promise<void> => {
    await turnOff();
    setIsConfirmingOff(false);
  };
  const handleToggle = (): void => {
    if (isAdvanced) setIsConfirmingOff(true);
    else void turnOn();
  };

  return (
    <div role="group" aria-label="Advanced mode switch" className="space-y-1 px-2">
      {canUseAdvanced ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-meta text-content-muted">
            Advanced mode · {isAdvanced ? "On" : "Off"}
          </span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={isPublishing || isSwitching}
            onClick={handleToggle}
          >
            {isAdvanced ? "Turn off" : "Turn on"}
          </Button>
        </div>
      ) : (
        <p className="text-micro text-content-faint">{ADVANCED_NARROW_NOTICE}</p>
      )}
      {isPublishing && <p className="text-micro text-content-faint">{PUBLISHING_NOTICE}</p>}
      <TurnOffDialog
        isOpen={isConfirmingOff}
        isBusy={isSwitching}
        missingPublishItems={missingPublishItems}
        onConfirm={() => void handleConfirmOff()}
        onCancel={() => setIsConfirmingOff(false)}
      />
    </div>
  );
};
