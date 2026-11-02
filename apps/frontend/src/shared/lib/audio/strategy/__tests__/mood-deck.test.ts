import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MOOD_FADE_STEP_MS, MoodDeck } from "../mood-deck";

function createDeck(fallback: string | null = "/audio/moods/peaceful.wav") {
  const attached: HTMLAudioElement[] = [];
  const deck = new MoodDeck({
    fadeSeconds: 1,
    attachChannel: (element) => attached.push(element),
    resolveFallbackUrl: () => fallback,
  });
  return { deck, attached };
}

describe("MoodDeck", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(async () => {});
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("crossfades between two channels instead of swapping one element's source", () => {
    const { deck, attached } = createDeck();
    deck.crossfadeTo("/a.mp3", true);
    vi.advanceTimersByTime(1000);
    deck.crossfadeTo("/b.mp3", true);
    vi.advanceTimersByTime(MOOD_FADE_STEP_MS * 5);

    const [first, second] = attached;
    expect(attached).toHaveLength(2);
    expect(first.volume).toBeCloseTo(0.5, 1);
    expect(second.volume).toBeCloseTo(0.5, 1);
  });

  it("silences and releases the outgoing channel when the fade completes", () => {
    const { deck, attached } = createDeck();
    deck.crossfadeTo("/a.mp3", true);
    vi.advanceTimersByTime(1000);
    deck.crossfadeTo("/b.mp3", true);
    vi.advanceTimersByTime(1000);

    expect(attached[0].volume).toBe(0);
    expect(attached[0].getAttribute("src")).toBeNull();
    expect(attached[1].volume).toBe(1);
  });

  it("falls back to the mood file when a stem fails to load", () => {
    const { deck, attached } = createDeck("/audio/moods/combat.wav");
    deck.crossfadeTo("/audio/strategy/stems/war.wav", true);

    attached[0].dispatchEvent(new Event("error"));

    expect(attached[0].src).toContain("/audio/moods/combat.wav");
  });

  it("stops everything on destroy", () => {
    const { deck, attached } = createDeck();
    deck.crossfadeTo("/a.mp3", true);

    deck.destroy();

    expect(attached[0].getAttribute("src")).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });
});
