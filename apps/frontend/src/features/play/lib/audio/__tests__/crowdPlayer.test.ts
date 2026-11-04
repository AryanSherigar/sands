import { describe, expect, it } from "vitest";
import {
  FakeAudioContext,
  type FakeBufferSource,
} from "@/shared/lib/audio/__tests__/fakeAudioContext";
import { CrowdPlayer } from "../crowdPlayer";

const CHEER = { mood: "cheer", intensity: 2 } as const;

function makePlayer(settings: { isMuted: boolean; volume: number }) {
  const context = new FakeAudioContext();
  const player = new CrowdPlayer(context as unknown as AudioContext, () => settings);
  return { context, player };
}

const startedSources = (context: FakeAudioContext): FakeBufferSource[] =>
  context.sources.filter((source) => source.hasStarted);

describe("CrowdPlayer", () => {
  it("plays a rendered reaction through a gain set to the player's volume", () => {
    const { context, player } = makePlayer({ isMuted: false, volume: 0.5 });
    player.play(CHEER);
    expect(startedSources(context)).toHaveLength(1);
    expect(context.gains[0]?.gain.value).toBe(0.5);
    expect(startedSources(context)[0]?.buffer?.length).toBeGreaterThan(0);
  });

  it("stays silent when audio is muted", () => {
    const { context, player } = makePlayer({ isMuted: true, volume: 0.5 });
    player.play(CHEER);
    expect(startedSources(context)).toHaveLength(0);
  });

  it("stays silent at zero volume", () => {
    const { context, player } = makePlayer({ isMuted: false, volume: 0 });
    player.play(CHEER);
    expect(startedSources(context)).toHaveLength(0);
  });

  it("resumes a suspended context so the first reaction is heard", () => {
    const { context, player } = makePlayer({ isMuted: false, volume: 1 });
    context.state = "suspended";
    player.play(CHEER);
    expect(context.state).toBe("running");
  });
});
