import { processPhoneEcho, renderBreathing } from "./phone-echo";

let sharedContext: AudioContext | null = null;

function audioContext(): AudioContext {
  sharedContext ??= new AudioContext();
  return sharedContext;
}

async function play(samples: Float32Array, sampleRate: number): Promise<void> {
  const context = audioContext();
  if (context.state === "suspended") await context.resume();
  const buffer = context.createBuffer(1, samples.length, sampleRate);
  buffer.getChannelData(0).set(samples);
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  return new Promise((resolve) => {
    source.onended = () => resolve();
    source.start();
  });
}

/** Plays the clip back processed; the clip never leaves this device. */
export async function playEcho(clip: Blob): Promise<void> {
  const decoded = await audioContext().decodeAudioData(await clip.arrayBuffer());
  const voice = decoded.getChannelData(0);
  await play(processPhoneEcho(voice, decoded.sampleRate), decoded.sampleRate);
}

export async function playBreathing(durationMs: number): Promise<void> {
  const sampleRate = audioContext().sampleRate;
  await play(renderBreathing(sampleRate, durationMs), sampleRate);
}
