import { describe, expect, it } from "vitest";
import { createAudioClock, createPerformanceClock } from "../composureClock";

describe("audio clock", () => {
  const makeSource = (time: number) => ({
    currentTime: time,
    suspend: () => Promise.resolve(),
    resume: () => Promise.resolve(),
  });

  it("reads audio time in milliseconds", () => {
    const clock = createAudioClock(makeSource(2.5), () => 9000);

    expect(clock.nowMs()).toBe(2500);
  });

  it("maps a performance timestamp onto audio time with the sampled offset", () => {
    const clock = createAudioClock(makeSource(2), () => 10_000);

    expect(clock.fromEventTime(10_500)).toBe(2500);
  });

  it("resamples the offset on resume and needs no schedule shift", () => {
    const source = makeSource(2);
    let perf = 10_000;
    const clock = createAudioClock(source, () => perf);
    clock.suspend();
    perf = 50_000;

    const shift = clock.resume();

    expect(shift).toBe(0);
    expect(clock.fromEventTime(50_300)).toBe(2300);
  });
});

describe("performance clock fallback", () => {
  it("uses performance time directly", () => {
    const clock = createPerformanceClock(() => 1234);

    expect(clock.nowMs()).toBe(1234);
    expect(clock.fromEventTime(99)).toBe(99);
  });

  it("reports how long it was suspended so the schedule can shift", () => {
    let perf = 1000;
    const clock = createPerformanceClock(() => perf);
    clock.suspend();
    perf = 4200;

    expect(clock.resume()).toBe(3200);
    expect(clock.resume()).toBe(0);
  });
});
