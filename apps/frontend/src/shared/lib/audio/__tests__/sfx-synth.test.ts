import { describe, expect, it } from "vitest";
import { SENSORY_CUE_IDS } from "@/shared/constants/sensory-cues";
import { synthesizeCue } from "../sfx-synth";
import { FakeAudioContext } from "./fakeAudioContext";

const synth = (cue: Parameters<typeof synthesizeCue>[1]) =>
  synthesizeCue(new FakeAudioContext() as unknown as BaseAudioContext, cue);

const peak = (data: Float32Array): number =>
  data.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

describe("synthesizeCue", () => {
  it("renders a non-empty, audible phone ring that never clips", () => {
    const buffer = synth("phone_ring");
    const data = buffer.getChannelData(0);

    expect(buffer.length).toBeGreaterThan(0);
    expect(peak(data)).toBeGreaterThan(0.1);
    expect(peak(data)).toBeLessThanOrEqual(1);
  });

  it("is deterministic: the same cue renders the same samples", () => {
    const first = synth("phone_ring").getChannelData(0);
    const second = synth("phone_ring").getChannelData(0);

    expect(Array.from(first)).toEqual(Array.from(second));
  });

  it("rings in bursts with silence between them", () => {
    const buffer = synth("phone_ring");
    const data = buffer.getChannelData(0);
    const windowSize = Math.floor(buffer.sampleRate * 0.05);
    const windows: number[] = [];
    for (let start = 0; start + windowSize <= data.length; start += windowSize) {
      windows.push(peak(data.slice(start, start + windowSize)));
    }

    expect(windows.some((level) => level > 0.1)).toBe(true);
    expect(windows.some((level) => level < 0.001)).toBe(true);
  });

  it("starts and ends at silence so it never clicks", () => {
    const data = synth("phone_ring").getChannelData(0);

    expect(Math.abs(data[0])).toBeLessThan(0.01);
    expect(Math.abs(data[data.length - 1])).toBeLessThan(0.01);
  });

  it("renders sudden_silence as dead air only", () => {
    const buffer = synth("sudden_silence");

    expect(buffer.length).toBeGreaterThan(0);
    expect(peak(buffer.getChannelData(0))).toBe(0);
  });

  it("renders a quiet, deterministic paper rustle that never clips", () => {
    const first = synth("paper_rustle").getChannelData(0);
    const second = synth("paper_rustle").getChannelData(0);

    expect(peak(first)).toBeGreaterThan(0.02);
    expect(peak(first)).toBeLessThan(0.5);
    expect(Array.from(first)).toEqual(Array.from(second));
  });

  it("rustles in separate crackles with gaps between them", () => {
    const buffer = synth("paper_rustle");
    const data = buffer.getChannelData(0);
    const windowSize = Math.floor(buffer.sampleRate * 0.01);
    const levels: number[] = [];
    for (let start = 0; start + windowSize <= data.length; start += windowSize) {
      levels.push(peak(data.slice(start, start + windowSize)));
    }

    expect(levels.some((level) => level > 0.02)).toBe(true);
    expect(levels.some((level) => level < 0.0001)).toBe(true);
  });
});

const AUDIBLE_CUES = SENSORY_CUE_IDS.filter((cue) => cue !== "sudden_silence");
const MAX_CUE_SECONDS = 4;

describe.each(AUDIBLE_CUES)("synthesizeCue %s", (cue) => {
  it("is audible, finite, never clips and has a sane length", () => {
    const buffer = synth(cue);
    const data = buffer.getChannelData(0);

    expect(Array.from(data).every(Number.isFinite)).toBe(true);
    expect(peak(data)).toBeGreaterThan(0.05);
    expect(peak(data)).toBeLessThanOrEqual(1);
    expect(buffer.duration).toBeGreaterThan(0.1);
    expect(buffer.duration).toBeLessThan(MAX_CUE_SECONDS);
  });

  it("renders the same samples every time", () => {
    expect(Array.from(synth(cue).getChannelData(0))).toEqual(
      Array.from(synth(cue).getChannelData(0)),
    );
  });

  it("does not end on a pop", () => {
    const data = synth(cue).getChannelData(0);

    expect(Math.abs(data[data.length - 1])).toBeLessThan(0.02);
  });
});

describe("synthesizeCue coverage", () => {
  it("renders a non-empty buffer for every cue id", () => {
    for (const cue of SENSORY_CUE_IDS) {
      expect(synth(cue).length).toBeGreaterThan(0);
    }
  });

  it("gives the cues distinct sounds", () => {
    const sounds = AUDIBLE_CUES.map((cue) => Array.from(synth(cue).getChannelData(0)).join(","));

    expect(new Set(sounds).size).toBe(AUDIBLE_CUES.length);
  });

  it("knocks three times with silence between", () => {
    const buffer = synth("heavy_knock");
    const data = buffer.getChannelData(0);
    const windowSize = Math.floor(buffer.sampleRate * 0.02);
    let isLoud = false;
    let onsets = 0;
    for (let start = 0; start + windowSize <= data.length; start += windowSize) {
      const level = peak(data.slice(start, start + windowSize));
      if (level > 0.3 && !isLoud) onsets += 1;
      isLoud = level > 0.05;
    }

    expect(onsets).toBe(3);
  });

  it("makes the lamp click louder than the room's other cues", () => {
    expect(peak(synth("lamp_click").getChannelData(0))).toBeGreaterThan(
      peak(synth("phone_ring").getChannelData(0)),
    );
  });

  it("chimes twice, the second note later than the first", () => {
    const buffer = synth("elevator_chime");
    const data = buffer.getChannelData(0);
    const secondStart = Math.floor(buffer.sampleRate * 0.5);
    const beforeSecond = peak(data.slice(secondStart - 40, secondStart));
    const atSecond = peak(data.slice(secondStart, secondStart + 400));

    expect(atSecond).toBeGreaterThan(beforeSecond);
  });
});
