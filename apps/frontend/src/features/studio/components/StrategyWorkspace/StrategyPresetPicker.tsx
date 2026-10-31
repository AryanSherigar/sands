import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { START_PRESETS, type StartPresetId } from "../../constants/strategyAuthoring";
import { applyPreset } from "../../lib/strategyStart";
import type { StrategyPresetPickerProps } from "./StrategyWorkspace.types";

const OVERWRITE_PROMPT = "This replaces your armies and relations. Continue?";

export const StrategyPresetPicker: React.FC<StrategyPresetPickerProps> = ({ fields, regions, onEdit }) => {
  const hasCustomisedStart = fields.armies.length > 0 || fields.relations.some((item) => item.status !== "peace");

  const handlePick = (presetId: StartPresetId): void => {
    if (hasCustomisedStart && !window.confirm(OVERWRITE_PROMPT)) return;
    onEdit((current) => applyPreset(current, presetId, regions));
  };

  return (
    <div className="flex flex-wrap gap-2">
      {START_PRESETS.map((preset) => (
        <Button key={preset.id} variant="secondary" size="sm" title={preset.description} onClick={() => handlePick(preset.id)}>
          {preset.label}
        </Button>
      ))}
    </div>
  );
};
