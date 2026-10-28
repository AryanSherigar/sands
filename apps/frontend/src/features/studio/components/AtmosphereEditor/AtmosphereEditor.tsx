import React from "react";
import { useDisplayHints } from "../../hooks/useDisplayHints";
import { AtmosphereEditorProps } from "./AtmosphereEditor.types";
import { CueLibrary } from "./CueLibrary";
import { ReaderEffectsForm } from "./ReaderEffectsForm";
import { TensionAudioForm } from "./TensionAudioForm";

export const AtmosphereEditor: React.FC<AtmosphereEditorProps> = ({
  scenarioId,
}) => {
  const { hints, saveHint, isSaving, error } = useDisplayHints(scenarioId);
  const meter = hints.meters[0];

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-content">Atmosphere</h1>
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
      <CueLibrary />
      {meter ? (
        <ReaderEffectsForm
          key={meter.path}
          path={meter.path}
          hint={meter.hint}
          isSaving={isSaving}
          onSave={saveHint}
        />
      ) : (
        <p className="text-xs text-content-faint">
          Add a meter in the HUD tab to give the reader effects something to follow.
        </p>
      )}
      {hints.tier ? (
        <TensionAudioForm
          key={hints.tier.path}
          path={hints.tier.path}
          hint={hints.tier.hint}
          options={hints.tier.options}
          isSaving={isSaving}
          onSave={saveHint}
        />
      ) : (
        <p className="text-xs text-content-faint">
          Add a tension tier in the HUD tab to choose music for each level.
        </p>
      )}
    </div>
  );
};
