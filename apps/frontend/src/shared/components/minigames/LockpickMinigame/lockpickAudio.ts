import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import type { ScenarioMood } from "@/shared/types/audio.types";

const TENSION_MOOD: ScenarioMood = "tension";
const MIN_GAIN = 0.0001;

let sharedAudioContext: AudioContext | null = null;
let masterGain: GainNode | null = null;
let isMuted = false;
let volume = 0.7;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const AudioCtxConstructor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!AudioCtxConstructor) return null;

  if (!sharedAudioContext) {
    sharedAudioContext = new AudioCtxConstructor();
    masterGain = sharedAudioContext.createGain();
    masterGain.gain.value = isMuted ? 0 : volume;
    masterGain.connect(sharedAudioContext.destination);
  }
  if (sharedAudioContext.state === "suspended") {
    void sharedAudioContext.resume();
  }
  return sharedAudioContext;
}

export function setLockpickMuted(muted: boolean): void {
  isMuted = muted;
  if (masterGain) {
    masterGain.gain.value = isMuted ? 0 : volume;
  }
}

export function setLockpickVolume(vol: number): void {
  volume = Math.max(0, Math.min(1, vol));
  if (masterGain && !isMuted) {
    masterGain.gain.value = volume;
  }
}

export function playDwellTick(): void {
  const ctx = getAudioContext();
  if (!ctx || !masterGain || isMuted) return;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(800, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.03);

  gain.gain.setValueAtTime(0.08, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(MIN_GAIN, ctx.currentTime + 0.03);

  osc.connect(gain);
  gain.connect(masterGain);
  osc.start();
  osc.stop(ctx.currentTime + 0.035);
}

export function playCylinderClick(): void {
  const ctx = getAudioContext();
  if (!ctx || !masterGain || isMuted) return;

  // Dual metallic tumbler snap
  const now = ctx.currentTime;

  const osc1 = ctx.createOscillator();
  const gain1 = ctx.createGain();
  osc1.type = "triangle";
  osc1.frequency.setValueAtTime(450, now);
  osc1.frequency.exponentialRampToValueAtTime(150, now + 0.08);
  gain1.gain.setValueAtTime(0.3, now);
  gain1.gain.exponentialRampToValueAtTime(MIN_GAIN, now + 0.08);

  const osc2 = ctx.createOscillator();
  const gain2 = ctx.createGain();
  osc2.type = "sine";
  osc2.frequency.setValueAtTime(1400, now + 0.02);
  osc2.frequency.exponentialRampToValueAtTime(600, now + 0.12);
  gain2.gain.setValueAtTime(0.25, now + 0.02);
  gain2.gain.exponentialRampToValueAtTime(MIN_GAIN, now + 0.12);

  osc1.connect(gain1);
  gain1.connect(masterGain);
  osc2.connect(gain2);
  gain2.connect(masterGain);

  osc1.start(now);
  osc1.stop(now + 0.09);
  osc2.start(now + 0.02);
  osc2.stop(now + 0.13);
}

export function playPickBreakSfx(): void {
  const ctx = getAudioContext();
  if (!ctx || !masterGain || isMuted) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sawtooth";
  osc.frequency.setValueAtTime(320, now);
  osc.frequency.exponentialRampToValueAtTime(60, now + 0.15);

  gain.gain.setValueAtTime(0.4, now);
  gain.gain.exponentialRampToValueAtTime(MIN_GAIN, now + 0.15);

  osc.connect(gain);
  gain.connect(masterGain);
  osc.start(now);
  osc.stop(now + 0.16);
}

export function playWinStinger(): void {
  const ctx = getAudioContext();
  if (!ctx || isMuted) return;

  const destination = masterGain ?? ctx.destination;
  const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6
  notes.forEach((freq, idx) => {
    const time = ctx.currentTime + idx * 0.08;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, time);
    gain.gain.setValueAtTime(0.2, time);
    gain.gain.exponentialRampToValueAtTime(MIN_GAIN, time + 0.25);

    osc.connect(gain);
    gain.connect(destination);
    osc.start(time);
    osc.stop(time + 0.26);
  });
}

export function playLoseStinger(): void {
  const ctx = getAudioContext();
  if (!ctx || isMuted) return;

  const destination = masterGain ?? ctx.destination;
  const notes = [440, 392, 349.23, 293.66]; // A4, G4, F4, D4
  notes.forEach((freq, idx) => {
    const time = ctx.currentTime + idx * 0.1;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(freq, time);
    gain.gain.setValueAtTime(0.25, time);
    gain.gain.exponentialRampToValueAtTime(MIN_GAIN, time + 0.2);

    osc.connect(gain);
    gain.connect(destination);
    osc.start(time);
    osc.stop(time + 0.22);
  });
}

export function enterMinigameAudio(): () => void {
  const previousMood = ambientSoundtrack.getMood();
  const previousTrackUrl = ambientSoundtrack.getCurrentTrackUrl();
  ambientSoundtrack.transitionTo(TENSION_MOOD, undefined, true);

  return () => {
    if (previousMood && previousTrackUrl) {
      ambientSoundtrack.transitionTo(previousMood, previousTrackUrl, true);
    }
  };
}
