import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { CueSequencer, QueuedCue } from "@/shared/lib/audio/cue-sequencer";
import { useAtmosphereStore } from "../stores/atmosphere.store";
import { PlaythroughData } from "../types/play.types";

// The play store hands cues here so it carries no audio sequencing itself.
const cueSequencer = new CueSequencer(ambientSoundtrack);

const ATMOSPHERE_TOOL_KEY = "atmosphere";
const STATUS_HUD_TOOL_KEY = "status_hud";
const RULE_REVEAL_CUE: QueuedCue = {
  cue: "paper_rustle",
  cut_ambient: false,
  silence_duration_ms: 0,
};

export function whenCuesIdle(): Promise<void> {
  return cueSequencer.whenIdle();
}

// While a tension tier maps to moods, the tier is the authority on the ambient
// track and the narrator's own `mood` events are ignored. A scenario without a
// `mood_map` keeps today's behaviour.
export function shouldIgnoreNarratorMood(
  playthrough: Pick<PlaythroughData, "enabled_tools" | "hud_hints"> | null,
): boolean {
  const tools = playthrough?.enabled_tools ?? [];
  if (!tools.includes(ATMOSPHERE_TOOL_KEY) || !tools.includes(STATUS_HUD_TOOL_KEY)) {
    return false;
  }
  const moodMap = playthrough?.hud_hints?.tier?.hint.mood_map;
  return moodMap !== undefined && Object.keys(moodMap).length > 0;
}

export function handleSensoryCue(cue: QueuedCue): void {
  cueSequencer.enqueue(cue);
  if (cue.cut_ambient) useAtmosphereStore.getState().triggerFlicker();
}

// A rule appearing on the clipboard rustles only for a scenario with Atmosphere
// on; the clipboard itself knows nothing about audio.
export function handleRuleRevealed(enabledTools: readonly string[]): void {
  if (!enabledTools.includes(ATMOSPHERE_TOOL_KEY)) return;
  cueSequencer.enqueue(RULE_REVEAL_CUE);
}
