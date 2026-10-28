import { beforeEach, describe, expect, it, vi } from "vitest";

const { enqueue } = vi.hoisted(() => ({ enqueue: vi.fn() }));
vi.mock("@/shared/lib/audio/cue-sequencer", () => ({
  CueSequencer: class {
    enqueue = enqueue;
  },
}));
vi.mock("@/shared/lib/audio/ambient-soundtrack", () => ({
  ambientSoundtrack: {},
}));

import { handleRuleRevealed } from "./atmosphereSubscriber";

describe("handleRuleRevealed", () => {
  beforeEach(() => enqueue.mockClear());

  it("plays a paper rustle over the ambience when atmosphere is on", () => {
    handleRuleRevealed(["rule_sheet", "atmosphere"]);

    expect(enqueue).toHaveBeenCalledWith({
      cue: "paper_rustle",
      cut_ambient: false,
      silence_duration_ms: 0,
    });
  });

  it("stays silent for a scenario without atmosphere", () => {
    handleRuleRevealed(["rule_sheet"]);

    expect(enqueue).not.toHaveBeenCalled();
  });
});
