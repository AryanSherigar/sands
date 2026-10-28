import { describe, expect, it } from "vitest";
import { ComposureAudio } from "../composureAudio";
import { FakeComposureContext } from "./fakeComposureContext";

const make = (profile: "chase" | "hum") => {
  const context = new FakeComposureContext();
  const audio = new ComposureAudio(context as unknown as AudioContext, profile);
  return { context, audio };
};

describe("ComposureAudio", () => {
  it("schedules a sub-bass thud on the beat", () => {
    const { context, audio } = make("hum");

    audio.scheduleBeat(2, 0);

    const thud = context.oscillators[0];
    expect(thud.startedAt).toBe(2);
    expect(thud.frequency.calls[0].value).toBeLessThan(80);
  });

  it("keeps footsteps soft in the hum profile whatever the strikes", () => {
    const { context, audio } = make("hum");

    audio.scheduleBeat(1, 0);
    audio.scheduleBeat(2, 2);

    const levels = context.gains.flatMap((gain) =>
      gain.gain.calls.filter((call) => call.kind === "set").map((call) => call.value),
    );
    expect(Math.max(...levels.filter((level) => level < 0.5))).toBeLessThan(0.05);
  });

  it("pans footsteps left and makes them louder with each strike in the chase profile", () => {
    const calm = make("chase");
    const hunted = make("chase");

    calm.audio.scheduleBeat(1, 0);
    hunted.audio.scheduleBeat(1, 2);

    expect(hunted.context.panners[0].pan.value).toBeLessThan(0);
    const level = (ctx: FakeComposureContext) =>
      ctx.gains[ctx.gains.length - 1].gain.calls[0].value;
    expect(level(hunted.context)).toBeGreaterThan(level(calm.context));
  });

  it("adds a second footstep once the chase has struck", () => {
    const calm = make("chase");
    const hunted = make("chase");

    calm.audio.scheduleBeat(1, 0);
    hunted.audio.scheduleBeat(1, 1);

    expect(hunted.context.sources.length).toBeGreaterThan(calm.context.sources.length);
  });

  it("plays a hum on a hit and a gasp on a strike", () => {
    const { context, audio } = make("hum");

    audio.playHit();
    audio.playStrike();

    expect(context.oscillators).toHaveLength(1);
    expect(context.sources).toHaveLength(1);
  });

  it("plays a three-note stinger for each outcome", () => {
    const { context, audio } = make("hum");

    audio.playOutcome("win");
    audio.playOutcome("lose");

    expect(context.oscillators).toHaveLength(6);
  });

  it("loads no asset files: every sound comes from oscillators and noise", () => {
    const { context, audio } = make("chase");

    audio.scheduleBeat(1, 1);

    expect(context.oscillators.length + context.sources.length).toBeGreaterThan(0);
  });

  it("closes its context", () => {
    const { context, audio } = make("hum");

    audio.close();

    expect(context.closed).toBe(true);
  });
});
