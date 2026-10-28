import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { FULL_EDITOR_VALUE_NOTE, TRACKED_VALUES_EMPTY_COPY } from "../../constants/trackedValues";
import { useOpenFullEditor } from "../../hooks/useOpenFullEditor";
import { useTrackedValueEditor } from "../../hooks/useTrackedValueEditor";
import { getGuideStep } from "../../lib/guideSteps";
import { isEditableValue, readPlayerSees } from "../../lib/trackedValueEditing";
import { humanizeKey } from "../../lib/valueOptions";
import { GuideStepLayout } from "./GuideStepLayout";
import { HudPreviewStrip } from "./advanced/HudPreviewStrip";
import { TrackedValueCard } from "./advanced/TrackedValueCard";
import { TurnOffToolPrompt } from "./advanced/TurnOffToolPrompt";
import { ValueQuickAdd } from "./advanced/ValueQuickAdd";

export const StepTrackedValues: React.FC = () => {
  const editor = useTrackedValueEditor();
  const openFullEditor = useOpenFullEditor();
  const existingLabels = new Set(
    editor.entries.map(([key, field]) => (field.label?.trim() || humanizeKey(key)).toLowerCase()),
  );
  const seesList = editor.entries.map(([, field]) => readPlayerSees(field));
  const availability = {
    isClockTaken: seesList.includes("clock"),
    isLevelsTaken: editor.entries.some(([, field]) => field.type === "enum" && readPlayerSees(field) === "levels"),
  };

  return (
    <GuideStepLayout step={getGuideStep("tracked_values")}>
      <HudPreviewStrip schema={editor.schema} />
      {editor.entries.length === 0 && (
        <p className="text-meta text-content-muted">{TRACKED_VALUES_EMPTY_COPY}</p>
      )}
      <div className="space-y-4">
        {editor.entries.map(([key, field]) =>
          isEditableValue(field) ? (
            <TrackedValueCard
              key={key}
              valueKey={key}
              field={field}
              availability={availability}
              onChange={(next) => void editor.writeField(key, next)}
              onDelete={() => editor.removeValue(key)}
            />
          ) : (
            <div
              key={key}
              className="flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-surface-raised p-4"
            >
              <p className="text-body text-content">{field.label?.trim() || humanizeKey(key)}</p>
              <Button type="button" variant="secondary" size="sm" onClick={openFullEditor}>
                {FULL_EDITOR_VALUE_NOTE}
              </Button>
            </div>
          ),
        )}
      </div>
      <ValueQuickAdd existingLabels={existingLabels} onAdd={(input) => void editor.addValue(input)} />
      <TurnOffToolPrompt tool={editor.hudTool} />
    </GuideStepLayout>
  );
};
