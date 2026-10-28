// NOTE: this roster must be verified against Gemini's current documented
// prebuilt-voice list for gemini-3.1-flash-tts-preview before treating it as
// final -- it mirrors the voice names TRS's app/turn/speaker_voice_pool.py
// uses, which carry the same verification caveat.
export interface NarratorVoiceDefinition {
  id: string;
  label: string;
  description: string;
}

export const NARRATOR_VOICES_CATALOG: NarratorVoiceDefinition[] = [
  { id: "Kore", label: "Kore", description: "Warm, measured" },
  { id: "Puck", label: "Puck", description: "Upbeat, playful" },
  { id: "Charon", label: "Charon", description: "Deep, grave" },
  { id: "Fenrir", label: "Fenrir", description: "Rough, intense" },
  { id: "Aoede", label: "Aoede", description: "Breathy, lyrical" },
  { id: "Orus", label: "Orus", description: "Firm, resolute" },
  { id: "Zephyr", label: "Zephyr", description: "Bright, airy" },
];

export const DEFAULT_NARRATOR_VOICE_ID = "Kore";

const CATALOG_BY_ID = new Map<string, NarratorVoiceDefinition>(
  NARRATOR_VOICES_CATALOG.map((voice) => [voice.id, voice]),
);

export function resolveNarratorVoice(
  id?: string | null,
): NarratorVoiceDefinition {
  if (!id) {
    return CATALOG_BY_ID.get(DEFAULT_NARRATOR_VOICE_ID)!;
  }
  return (
    CATALOG_BY_ID.get(id) ?? CATALOG_BY_ID.get(DEFAULT_NARRATOR_VOICE_ID)!
  );
}
