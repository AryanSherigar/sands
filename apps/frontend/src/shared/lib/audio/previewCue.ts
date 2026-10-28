import type { SensoryCueId } from "@/shared/constants/sensory-cues";
import { SfxPlayer } from "./sfx-player";

let sharedPlayer: SfxPlayer | null = null;
let sharedContext: AudioContext | null = null;

export type CuePreviewResult = "played" | "blocked";

// Plays one cue through the same synthesiser (or recording) the play screen
// uses. Browsers refuse audio before a click, which is reported, not thrown.
export async function previewCue(cue: SensoryCueId): Promise<CuePreviewResult> {
  try {
    sharedContext ??= new AudioContext();
    sharedPlayer ??= new SfxPlayer(sharedContext);
    if (sharedContext.state === "suspended") await sharedContext.resume();
    const buffer = await sharedPlayer.getBuffer(cue);
    const source = sharedContext.createBufferSource();
    source.buffer = buffer;
    source.connect(sharedContext.destination);
    source.start();
    return "played";
  } catch {
    return "blocked";
  }
}
