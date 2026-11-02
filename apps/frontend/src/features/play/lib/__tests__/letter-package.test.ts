import { describe, expect, it } from "vitest";
import type { SceneViewResponse } from "../../types/scene.types";
import { buildLetterPackage } from "../letter-package";

const VIEW: SceneViewResponse = {
  scene_id: "scene-9",
  scene_type: "letter",
  status: "opened",
  turn: 8,
  initiator: "ai",
  is_declinable: true,
  situation: {
    summary: "Mira of Ashford writes to Valdren with a warning.",
    facts: [{ label: "Topic", value: "warning" }],
  },
  participants: [
    {
      participant_id: "mira",
      kind: "leader",
      name: "Mira of Ashford",
      trait_ids: ["cunning", "proud"],
    },
  ],
  transcript: [],
  exchanges_remaining: 1,
};

describe("buildLetterPackage", () => {
  it("names the sender from the scene's leader and the dispatch from its turn", () => {
    const pkg = buildLetterPackage(VIEW, "First.\n\nSecond.");
    expect(pkg.sceneId).toBe("scene-9");
    expect(pkg.dispatchNumber).toBe(8);
    expect(pkg.provenance.senderName).toBe("Mira of Ashford");
  });

  it("shows the incoming letter as its paragraphs", () => {
    const pkg = buildLetterPackage(VIEW, "First.\n\nSecond.");
    expect(pkg.incoming.paragraphs).toEqual(["First.", "Second."]);
  });

  it("starts the player's draft empty", () => {
    const pkg = buildLetterPackage(VIEW, "Text");
    expect(pkg.initialDraft.paragraphs).toEqual([""]);
    expect(pkg.initialDraft.instruction).toBe("");
  });

  it("carries declinability from the scene", () => {
    expect(buildLetterPackage(VIEW, "Text").isDeclinable).toBe(true);
    expect(
      buildLetterPackage({ ...VIEW, is_declinable: false }, "Text").isDeclinable,
    ).toBe(false);
  });

  it("describes the topic in the sender's temperament without inventing facts", () => {
    const pkg = buildLetterPackage(VIEW, "Text");
    expect(pkg.provenance.temperament).toMatch(/warning/i);
    expect(pkg.provenance.portraitUrl).toBe("");
  });

  it("falls back to a neutral sender name when the scene has no leader", () => {
    const pkg = buildLetterPackage({ ...VIEW, participants: [] }, "Text");
    expect(pkg.provenance.senderName).toBe("A rival ruler");
  });
});
