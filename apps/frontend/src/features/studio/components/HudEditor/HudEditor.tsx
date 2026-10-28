import React from "react";
import { useDisplayHints } from "../../hooks/useDisplayHints";
import { listEnumFields, listNumberFields } from "../../lib/stateSchemaFields";
import { ClockHintForm } from "./ClockHintForm";
import { HudEditorProps } from "./HudEditor.types";
import { HudPreview } from "./HudPreview";
import { MeterHintForm } from "./MeterHintForm";
import { TierHintForm } from "./TierHintForm";

export const HudEditor: React.FC<HudEditorProps> = ({ scenarioId }) => {
  const { stateSchema, hints, saveHint, isSaving, error } =
    useDisplayHints(scenarioId);
  const numberFields = listNumberFields(stateSchema);
  const enumFields = listEnumFields(stateSchema);
  const meterFields = hints.meters.map(({ path, hint }) => ({
    path,
    label: hint.label,
  }));
  const unusedMeterFields = numberFields.filter(
    (field) => !hints.meters.some((meter) => meter.path === field.path),
  );

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-content">HUD</h1>
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
      <ClockHintForm
        key={hints.clock?.path ?? "new-clock"}
        current={hints.clock}
        numberFields={numberFields}
        meterFields={meterFields}
        isSaving={isSaving}
        onSave={saveHint}
        onRemove={(path) => saveHint(path, null)}
      />
      {hints.meters.map((meter) => (
        <MeterHintForm
          key={meter.path}
          current={meter}
          numberFields={numberFields}
          isSaving={isSaving}
          onSave={saveHint}
          onRemove={(path) => saveHint(path, null)}
        />
      ))}
      {unusedMeterFields.length > 0 && (
        <MeterHintForm
          key={`new-meter-${hints.meters.length}`}
          current={undefined}
          numberFields={unusedMeterFields}
          isSaving={isSaving}
          onSave={saveHint}
          onRemove={(path) => saveHint(path, null)}
        />
      )}
      <TierHintForm
        key={hints.tier?.path ?? "new-tier"}
        current={hints.tier}
        enumFields={enumFields}
        isSaving={isSaving}
        onSave={saveHint}
        onRemove={(path) => saveHint(path, null)}
      />
      <HudPreview hints={hints} />
    </div>
  );
};
