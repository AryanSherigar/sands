import { beforeEach, describe, expect, it, vi } from "vitest";
import { CueSequencer, CueSequencerAudio } from "../cue-sequencer";

const SILENCE_MS = 800;

interface Step {
  step: string;
  detail?: unknown;
}

const createAudio = () => {
  const steps: Step[] = [];
  const releaseSfx: Array<() => void> = [];
  const audio: CueSequencerAudio = {
    hardMute: vi.fn((durationMs?: number) => {
      steps.push({ step: "cut", detail: durationMs });
    }),
    playSfx: vi.fn(
      (cue: string, options: { leadSilenceMs: number }) =>
        new Promise<void>((resolve) => {
          steps.push({ step: "sfx", detail: { cue, ...options } });
          releaseSfx.push(resolve);
        }),
    ),
    resumeAmbient: vi.fn((rampMs: number) => {
      steps.push({ step: "resume", detail: rampMs });
    }),
  };
  return { audio, steps, releaseSfx };
};

const cue = (name: string, overrides = {}) => ({
  cue: name as never,
  cut_ambient: true,
  silence_duration_ms: SILENCE_MS,
  ...overrides,
});

const flush = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

describe("CueSequencer", () => {
  let fixture: ReturnType<typeof createAudio>;
  let sequencer: CueSequencer;

  beforeEach(() => {
    fixture = createAudio();
    sequencer = new CueSequencer(fixture.audio);
  });

  it("runs hard cut, then the gap and sound, then resumes the ambience", async () => {
    sequencer.enqueue(cue("phone_ring"));
    await flush();
    fixture.releaseSfx[0]();
    await flush();

    expect(fixture.steps.map((s) => s.step)).toEqual(["cut", "sfx", "resume"]);
    expect(fixture.steps[1].detail).toEqual({
      cue: "phone_ring",
      leadSilenceMs: SILENCE_MS,
    });
  });

  it("makes the cut fast", async () => {
    sequencer.enqueue(cue("phone_ring"));
    await flush();

    expect(fixture.audio.hardMute).toHaveBeenCalledWith(30);
  });

  it("uses the authored dead-air gap as the lead silence", async () => {
    sequencer.enqueue(cue("phone_ring", { silence_duration_ms: 2500 }));
    await flush();

    expect(fixture.steps[1].detail).toMatchObject({ leadSilenceMs: 2500 });
  });

  it("goes straight to the sound when the cue does not cut the ambience", async () => {
    sequencer.enqueue(cue("paper_rustle", { cut_ambient: false }));
    await flush();
    fixture.releaseSfx[0]();
    await flush();

    expect(fixture.steps.map((s) => s.step)).toEqual(["sfx"]);
    expect(fixture.steps[0].detail).toMatchObject({ leadSilenceMs: 0 });
  });

  it("queues cues first in, first out and never overlaps them", async () => {
    sequencer.enqueue(cue("phone_ring"));
    sequencer.enqueue(cue("heavy_knock"));
    await flush();

    expect(fixture.audio.playSfx).toHaveBeenCalledTimes(1);
    fixture.releaseSfx[0]();
    await flush();
    fixture.releaseSfx[1]();
    await flush();

    expect(
      (fixture.audio.playSfx as ReturnType<typeof vi.fn>).mock.calls.map(
        (call) => call[0],
      ),
    ).toEqual(["phone_ring", "heavy_knock"]);
  });

  it("cuts once for a burst of cues and resumes once at the end", async () => {
    sequencer.enqueue(cue("phone_ring"));
    sequencer.enqueue(cue("heavy_knock"));
    await flush();
    fixture.releaseSfx[0]();
    await flush();
    fixture.releaseSfx[1]();
    await flush();

    expect(fixture.steps.map((s) => s.step)).toEqual([
      "cut",
      "sfx",
      "sfx",
      "resume",
    ]);
    expect(fixture.steps[2].detail).toMatchObject({ leadSilenceMs: 0 });
  });

  it("accepts a cue that arrives while another is playing", async () => {
    sequencer.enqueue(cue("phone_ring"));
    await flush();
    sequencer.enqueue(cue("lamp_click"));
    fixture.releaseSfx[0]();
    await flush();
    fixture.releaseSfx[1]();
    await flush();

    expect(fixture.audio.playSfx).toHaveBeenCalledTimes(2);
  });

  it("drops queued cues and resumes the ambience when cancelled", async () => {
    sequencer.enqueue(cue("phone_ring"));
    sequencer.enqueue(cue("heavy_knock"));
    await flush();

    sequencer.cancel();
    fixture.releaseSfx[0]();
    await flush();

    expect(fixture.audio.playSfx).toHaveBeenCalledTimes(1);
    expect(fixture.steps.at(-1)?.step).toBe("resume");
  });

  it("recovers from a failing sound and still resumes the ambience", async () => {
    fixture.audio.playSfx = vi.fn(() => Promise.reject(new Error("decode")));
    sequencer = new CueSequencer(fixture.audio);

    sequencer.enqueue(cue("phone_ring"));
    await flush();
    await flush();

    expect(fixture.audio.resumeAmbient).toHaveBeenCalled();
  });
});

describe("CueSequencer whenIdle", () => {
  it("resolves at once when nothing is running", async () => {
    const sequencer = new CueSequencer({
      hardMute: vi.fn(),
      playSfx: vi.fn().mockResolvedValue(undefined),
      resumeAmbient: vi.fn(),
    });

    await expect(sequencer.whenIdle()).resolves.toBeUndefined();
  });

  it("resolves only after the ambience has been resumed", async () => {
    const events: string[] = [];
    let finishSound: () => void = () => {};
    const sequencer = new CueSequencer({
      hardMute: () => events.push("cut"),
      playSfx: () =>
        new Promise<void>((resolve) => {
          finishSound = resolve;
        }),
      resumeAmbient: () => events.push("resume"),
    });

    sequencer.enqueue({ cue: "phone_ring", cut_ambient: true, silence_duration_ms: 0 });
    const idle = sequencer.whenIdle().then(() => events.push("idle"));
    finishSound();
    await idle;

    expect(events).toEqual(["cut", "resume", "idle"]);
  });
});
