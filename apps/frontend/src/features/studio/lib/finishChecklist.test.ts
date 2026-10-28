import { describe, expect, it } from "vitest";
import { buildScenarioFixture } from "../test/studioApiMock";
import {
  describeMissingRequired,
  getRequiredItems,
  getSuggestions,
  hasOpeningText,
} from "./finishChecklist";

describe("finishChecklist", () => {
  it("marks Name, One line idea and Opening as missing on an empty story", () => {
    const items = getRequiredItems(buildScenarioFixture());
    expect(items.map((item) => [item.label, item.isDone])).toEqual([
      ["Name", false],
      ["One line idea", false],
      ["Opening", false],
    ]);
    expect(describeMissingRequired(items)).toBe(
      "To publish, add: Name, One line idea, Opening.",
    );
  });

  it("names only what is still missing and returns null when complete", () => {
    const partial = getRequiredItems(
      buildScenarioFixture({ title: "The Door Below", logline: "A door in the sea." }),
    );
    expect(describeMissingRequired(partial)).toBe("To publish, add: Opening.");

    const complete = getRequiredItems(
      buildScenarioFixture({
        title: "The Door Below",
        logline: "A door in the sea.",
        opening_scene: "The tide is out.",
      }),
    );
    expect(describeMissingRequired(complete)).toBeNull();
  });

  it("treats whitespace-only values as missing", () => {
    const items = getRequiredItems(buildScenarioFixture({ title: "   ", logline: "\n" }));
    expect(items[0].isDone).toBe(false);
    expect(items[1].isDone).toBe(false);
  });

  it("counts an opening document as an opening before the rendered text is saved", () => {
    const scenario = buildScenarioFixture({
      world_data: { openingDocument: { blocks: [{ kind: "text", text: "Rain." }] } },
    });
    expect(hasOpeningText(scenario)).toBe(true);
    expect(hasOpeningText(null)).toBe(false);
  });

  it("lists quiet suggestions that point at the step that fixes them", () => {
    const suggestions = getSuggestions(buildScenarioFixture(), 0);
    expect(suggestions.map((item) => [item.id, item.isDone, item.fixStep])).toEqual([
      ["premise", false, 2],
      ["genre", false, 2],
      ["characters", false, 4],
    ]);
  });

  it("marks suggestions done once the story has them", () => {
    const suggestions = getSuggestions(
      buildScenarioFixture({
        genre_tags: ["Mystery"],
        world_data: { premiseDocument: { blocks: [{ kind: "text", text: "Mara keeps a light." }] } },
      }),
      2,
    );
    expect(suggestions.every((item) => item.isDone)).toBe(true);
  });
});
