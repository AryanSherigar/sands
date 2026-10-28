import React, { useEffect, useRef, useState } from "react";
import { Select, SelectOptionGroup } from "@/shared/components/ui/Select";
import {
  DEFAULT_NARRATOR_VOICE_ID,
  NARRATOR_VOICES_CATALOG,
  resolveNarratorVoice,
} from "@/shared/constants/narrator-voices";
import { useScenario } from "../../hooks/useScenario";
import { NarratorVoicePickerProps } from "./NarratorVoicePicker.types";

const VOICE_GROUPS: SelectOptionGroup[] = [
  {
    label: "Narrator Voice",
    options: NARRATOR_VOICES_CATALOG.map((voice) => ({
      value: voice.id,
      label: `${voice.label} — ${voice.description}`,
    })),
  },
];

export const NarratorVoicePicker: React.FC<NarratorVoicePickerProps> = ({
  scenarioId,
}) => {
  const { scenario, isLoading, updateScenario } = useScenario(scenarioId);
  const [voiceId, setVoiceId] = useState<string>(DEFAULT_NARRATOR_VOICE_ID);
  const hasInitialized = useRef(false);

  useEffect(() => {
    if (scenario && !hasInitialized.current) {
      const resolved = resolveNarratorVoice(scenario.narrator_voice_name);
      setVoiceId(resolved.id);
      hasInitialized.current = true;
    }
  }, [scenario]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const nextVoiceId = e.target.value;
    setVoiceId(nextVoiceId);
    updateScenario({ narrator_voice_name: nextVoiceId });
  };

  if (isLoading) {
    return (
      <p className="text-sm text-content-faint">Loading narrator voice...</p>
    );
  }

  return (
    <div className="space-y-2">
      <h2 className="text-base font-semibold text-content">Narrator Voice</h2>
      <Select
        aria-label="Narrator voice"
        groups={VOICE_GROUPS}
        value={voiceId}
        onChange={handleChange}
      />
    </div>
  );
};
