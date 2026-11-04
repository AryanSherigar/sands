import type { CrowdReaction } from "../../types/battleSpeech.types";
import { renderCrowdReaction } from "./crowdSynth";

const MONO_CHANNEL_COUNT = 1;
const FIRST_CHANNEL = 0;

export interface CrowdPlayerSettings {
  isMuted: boolean;
  volume: number;
}

export class CrowdPlayer {
  private readonly context: AudioContext;
  private readonly readSettings: () => CrowdPlayerSettings;

  constructor(context: AudioContext, readSettings: () => CrowdPlayerSettings) {
    this.context = context;
    this.readSettings = readSettings;
  }

  play(reaction: CrowdReaction): void {
    const { isMuted, volume } = this.readSettings();
    if (isMuted || volume <= 0) return;
    if (this.context.state === "suspended") void this.context.resume();
    const samples = renderCrowdReaction(reaction, this.context.sampleRate);
    const buffer = this.context.createBuffer(MONO_CHANNEL_COUNT, samples.length, this.context.sampleRate);
    buffer.getChannelData(FIRST_CHANNEL).set(samples);
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    const gain = this.context.createGain();
    gain.gain.value = volume;
    source.connect(gain);
    gain.connect(this.context.destination);
    source.start();
  }
}
