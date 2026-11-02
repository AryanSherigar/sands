import { describe, expect, it } from "vitest";
import { buildJudgmentPackage } from "../judgment-package";
import type { SceneViewResponse } from "../../types/scene.types";

const OPENING = "The hall is silent.\nBRANNOCH: \"An open defiance requires an open reckoning.\"";

const view = (overrides: Partial<SceneViewResponse> = {}): SceneViewResponse => ({
  scene_id: "scene-j",
  scene_type: "judgment",
  status: "opened",
  turn: 5,
  initiator: "ai",
  is_declinable: false,
  situation: {
    summary: "Harl, governor of Ash Ford, stands accused before Valdren.",
    facts: [
      { label: "Accused", value: "Harl" },
      { label: "Charge", value: "an uprising in their region has been crushed" },
    ],
  },
  participants: [
    { participant_id: "harl", kind: "governor", name: "Harl", trait_ids: ["proud"] },
    {
      participant_id: "veyra",
      kind: "governor",
      name: "Veyra",
      trait_ids: [],
      stance: "mercy",
    },
    {
      participant_id: "brannoch",
      kind: "officer",
      name: "Brannoch",
      trait_ids: [],
      stance: "iron",
    },
  ],
  transcript: [
    { sequence: 1, player_text: "", leader_text: OPENING },
    { sequence: 2, player_text: "Why did you rise?", leader_text: "HARL: \"Bread.\"" },
  ],
  exchanges_remaining: 4,
  ...overrides,
});

describe("buildJudgmentPackage", () => {
  it("maps the accused, the advisors with their stances, and the charge", () => {
    const pkg = buildJudgmentPackage(view());
    expect(pkg.sceneId).toBe("scene-j");
    expect(pkg.subjectKind).toBe("governor");
    expect(pkg.accused.name).toBe("Harl");
    expect(pkg.advisors.map((item) => [item.name, item.stance])).toEqual([
      ["Veyra", "mercy"],
      ["Brannoch", "iron"],
    ]);
    expect(pkg.charge).toBe("an uprising in their region has been crushed");
  });

  it("takes the opening from the first exchange and the spoken ones from the rest", () => {
    const pkg = buildJudgmentPackage(view());
    expect(pkg.openingText).toBe(OPENING);
    expect(pkg.exchanges).toEqual([
      { sequence: 2, playerText: "Why did you rise?", courtText: 'HARL: "Bread."' },
    ]);
  });

  it("keeps one exchange back for the pronouncement", () => {
    expect(buildJudgmentPackage(view()).spokenExchangesRemaining).toBe(3);
    expect(buildJudgmentPackage(view({ exchanges_remaining: 1 })).spokenExchangesRemaining).toBe(0);
  });

  it("treats a captive noble as a captive and tolerates a court of one", () => {
    const pkg = buildJudgmentPackage(
      view({
        participants: [
          { participant_id: "ser_orrin", kind: "commander", name: "Ser Orrin", trait_ids: [] },
          { participant_id: "veyra", kind: "governor", name: "Veyra", trait_ids: [], stance: "mercy" },
        ],
      }),
    );
    expect(pkg.subjectKind).toBe("captive");
    expect(pkg.advisors).toHaveLength(1);
  });

  it("carries the outcome summary once the scene has resolved", () => {
    const pkg = buildJudgmentPackage(
      view({
        status: "resolved",
        outcome: { kind: "judgment", verdict: "exile", nuance: null },
        outcome_summary: ["Judgment: Exiled."],
        exchanges_remaining: 0,
      }),
    );
    expect(pkg.isResolved).toBe(true);
    expect(pkg.outcomeSummary).toEqual(["Judgment: Exiled."]);
  });

  it("has an empty opening before the court has been convened", () => {
    expect(buildJudgmentPackage(view({ transcript: [] })).openingText).toBe("");
  });
});
