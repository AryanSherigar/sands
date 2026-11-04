import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { START_PRESETS, type StartPresetId } from "../../constants/strategyAuthoring";
import { applyPreset } from "../../lib/strategyStart";
import type { StrategyPresetPickerProps } from "./StrategyWorkspace.types";

const OVERWRITE_PROMPT = "This replaces your armies and relations. Continue?";

export const StrategyPresetPicker: React.FC<StrategyPresetPickerProps> = ({ fields, regions, onEdit }) => {
  const [pendingPresetId, setPendingPresetId] = useState<StartPresetId | null>(null);
  const hasCustomisedStart = fields.armies.length > 0 || fields.relations.some((item) => item.status !== "peace");

  const applyPresetById = (presetId: StartPresetId): void => {
    onEdit((current) => applyPreset(current, presetId, regions));
  };

  const handlePick = (presetId: StartPresetId): void => {
    if (hasCustomisedStart) {
      setPendingPresetId(presetId);
      return;
    }
    applyPresetById(presetId);
  };

  const handleConfirm = (): void => {
    if (pendingPresetId) applyPresetById(pendingPresetId);
    setPendingPresetId(null);
  };

  return (
    <div className="flex flex-wrap gap-2">
      {START_PRESETS.map((preset) => (
        <Button key={preset.id} variant="secondary" size="sm" title={preset.description} onClick={() => handlePick(preset.id)}>
          {preset.label}
        </Button>
      ))}
      <Modal
        isOpen={pendingPresetId !== null}
        onClose={() => setPendingPresetId(null)}
        title="Replace your starting situation?"
        size="narrow"
      >
        <p className="text-sm text-content-muted">{OVERWRITE_PROMPT}</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setPendingPresetId(null)}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={handleConfirm}>
            Replace
          </Button>
        </div>
      </Modal>
    </div>
  );
};
