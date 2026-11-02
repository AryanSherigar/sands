import { describe, expect, it } from "vitest";
import { buildFantasyViewModel } from "../buildFantasyViewModel";
import type { PlaythroughData } from "../../types/play.types";

describe("buildFantasyViewModel", () => {
  it("uses visible live attributes and latest available image", () => {
    const playthrough = {
      entities: [
        { entity_id: "a", entity_type: "character", canonical_name: "Veya", description: "Innkeeper", attributes: { standing: 99 }, attributes_schema: { standing: { type: "number", label: "Standing" }, present: { type: "boolean" } } },
        { entity_id: "l", entity_type: "location", canonical_name: "Inn", attributes: {}, attributes_schema: {} },
      ],
      state: { current_location_id: "l", entities: { a: { standing: 0, present: false, hidden: "secret" } } },
      turns: [{ id: "1", image_url: "image" }, { id: "2" }],
    } as unknown as PlaythroughData;
    const result = buildFantasyViewModel(playthrough);
    expect(result.location).toBe("Inn");
    expect(result.sceneImage).toEqual({ turnId: "1", url: "image" });
    expect(result.characters[0].attributes).toEqual([{ label: "Standing", value: 0 }, { label: "present", value: false }]);
  });
});

it("does not invent world values or relationship interpretations", () => {
  const playthrough = {
    scenario_title: "Another World", entities: [{ entity_id: "a", entity_type: "character", canonical_name: "Veya", description: null, attributes_schema: { standing: { type: "number", label: "Standing" } } }],
    state: { player: { coins: 3, energy: 12 }, entities: { a: { standing: 2 } } },
    turns: [], player_stats: [], player_inventory: [], objectives: [{ outcome_title: "Find a path", outcome_tag: "win", outcome_text: "Explore." }], action_chips: [],
  } as unknown as PlaythroughData;
  const result = buildFantasyViewModel(playthrough);
  expect(result.status.locale).toBeNull();
  expect(result.status.energy).toBeNull();
  expect(result.status.vault?.label).toBe("3");
  expect(result.characters[0].disposition).toBeNull();
  expect(result.currentAccord?.stageProgress).toBeNull();
});
