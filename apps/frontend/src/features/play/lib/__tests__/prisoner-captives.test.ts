import { describe, expect, it } from "vitest";
import { prisonersToCaptives } from "../prisoner-captives";
import type { PrisonerView } from "../../types/simulation.types";

const prisoner = (overrides: Partial<PrisonerView> = {}): PrisonerView => ({
  id: "captive_1",
  name: "Ser Orrin",
  title: "Commander",
  origin_faction_id: "house_ashford",
  ransom_value_gold: 120,
  sentence_ends_turn: null,
  ...overrides,
});

describe("prisonersToCaptives", () => {
  it("maps held nobles onto the captives shown after a battle", () => {
    expect(prisonersToCaptives([prisoner()])).toEqual([
      {
        nobleId: "captive_1",
        name: "Ser Orrin",
        title: "Commander",
        factionId: "house_ashford",
        ransomValueGold: 120,
      },
    ]);
  });

  it("returns an empty list when there are no prisoners or the list is missing", () => {
    expect(prisonersToCaptives([])).toEqual([]);
    expect(prisonersToCaptives(undefined)).toEqual([]);
  });

  it("leaves out prisoners already serving a sentence", () => {
    expect(prisonersToCaptives([prisoner({ sentence_ends_turn: 9 })])).toEqual([]);
  });
});
