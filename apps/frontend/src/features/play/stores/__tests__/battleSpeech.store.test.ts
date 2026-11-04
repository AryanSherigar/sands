import { beforeEach, describe, expect, it } from "vitest";
import { useBattleSpeechStore } from "../battleSpeech.store";

const CHEER = { mood: "cheer", intensity: 2 } as const;

describe("battleSpeech store", () => {
  beforeEach(() => useBattleSpeechStore.getState().reset());

  it("starts by showing the officer's report", () => {
    expect(useBattleSpeechStore.getState().phase).toBe("report");
    expect(useBattleSpeechStore.getState().lastReaction).toBeNull();
  });

  it("moves from report to talking when the player starts", () => {
    useBattleSpeechStore.getState().beginTalking();
    expect(useBattleSpeechStore.getState().phase).toBe("talking");
  });

  it("shows a reaction after a talk and returns to talking when more talks remain", () => {
    useBattleSpeechStore.getState().showReaction(CHEER);
    expect(useBattleSpeechStore.getState().phase).toBe("reacting");
    expect(useBattleSpeechStore.getState().lastReaction).toEqual(CHEER);
    useBattleSpeechStore.getState().continueAfterReaction(false);
    expect(useBattleSpeechStore.getState().phase).toBe("talking");
  });

  it("goes to the result after the closing reaction", () => {
    useBattleSpeechStore.getState().showReaction(CHEER);
    useBattleSpeechStore.getState().continueAfterReaction(true);
    expect(useBattleSpeechStore.getState().phase).toBe("result");
  });

  it("resets for the next battle", () => {
    useBattleSpeechStore.getState().showReaction(CHEER);
    useBattleSpeechStore.getState().reset();
    expect(useBattleSpeechStore.getState().phase).toBe("report");
    expect(useBattleSpeechStore.getState().lastReaction).toBeNull();
  });
});
