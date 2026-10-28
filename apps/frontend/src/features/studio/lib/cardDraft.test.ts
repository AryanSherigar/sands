import { describe, expect, it } from "vitest";
import {
  addTrigger,
  buildCardDraft,
  buildDuplicatePayload,
  buildEntityUpdate,
  buildNewCardPayload,
  removeTrigger,
  renameTrigger,
} from "./cardDraft";
import { buildEntityFixture } from "../test/cardApiMock";

describe("cardDraft", () => {
  it("renameTrigger replaces the old name in place", () => {
    expect(renameTrigger(["Mara", "the keeper"], "Mara", "Maria")).toEqual([
      "Maria",
      "the keeper",
    ]);
  });

  it("renameTrigger leaves the list alone when the old name was removed", () => {
    expect(renameTrigger(["the keeper"], "Mara", "Maria")).toEqual(["the keeper"]);
  });

  it("addTrigger trims, ignores blanks and rejects duplicates", () => {
    expect(addTrigger(["Mara"], "  the keeper ")).toEqual(["Mara", "the keeper"]);
    expect(addTrigger(["Mara"], "   ")).toEqual(["Mara"]);
    expect(addTrigger(["Mara"], "mara")).toEqual(["Mara"]);
  });

  it("removeTrigger drops only the chosen trigger", () => {
    expect(removeTrigger(["Mara", "the keeper"], "Mara")).toEqual(["the keeper"]);
  });

  it("buildCardDraft wraps an old plain description as one text block", () => {
    const entity = buildEntityFixture({
      entity_id: "e1",
      canonical_name: "Mara",
      description: "The keeper.",
      lore_document: null,
    });

    expect(buildCardDraft(entity).lore.blocks).toEqual([
      { kind: "text", text: "The keeper." },
    ]);
  });

  it("buildCardDraft prefers the stored lore document", () => {
    const entity = buildEntityFixture({
      entity_id: "e1",
      canonical_name: "Mara",
      description: "ignored",
      lore_document: { blocks: [{ kind: "text", text: "From the box." }] },
    });

    expect(buildCardDraft(entity).lore.blocks[0].text).toBe("From the box.");
  });

  it("buildEntityUpdate sends the name, triggers and lore box", () => {
    const draft = {
      name: "Mara",
      aliases: ["Mara"],
      lore: { blocks: [] },
    };

    expect(buildEntityUpdate(draft)).toEqual({
      canonical_name: "Mara",
      aliases: ["Mara"],
      lore_document: { blocks: [] },
    });
  });

  it("buildNewCardPayload maps the card kind and seeds the name as a trigger", () => {
    expect(buildNewCardPayload({ kind: "place", name: "Lighthouse" })).toMatchObject({
      entity_type: "location",
      canonical_name: "Lighthouse",
      aliases: ["Lighthouse"],
      lore_document: { blocks: [] },
    });
  });

  it("buildNewCardPayload uses a plain default name and marks the player card", () => {
    const payload = buildNewCardPayload({ kind: "character", isPlayer: true });

    expect(payload.canonical_name).toBe("New character");
    expect(payload.aliases).toEqual(["New character"]);
    expect(payload.is_player).toBe(true);
  });

  it("buildNewCardPayload uses the creator's own type for Other cards", () => {
    expect(
      buildNewCardPayload({ kind: "other", entityType: "ship", name: "The Ardent" }),
    ).toMatchObject({ entity_type: "ship" });
  });
});

describe("buildDuplicatePayload", () => {
  it("copies type, lore and triggers under a new name, never as the player", () => {
    const entity = buildEntityFixture({
      entity_id: "e1",
      canonical_name: "Mara",
      aliases: ["Mara", "the keeper"],
      is_player: true,
      lore_document: { blocks: [{ kind: "text", text: "Keeps the light." }] },
    });

    const payload = buildDuplicatePayload(entity);

    expect(payload).toEqual({
      entity_type: "character",
      canonical_name: "Mara copy",
      aliases: ["Mara copy", "the keeper"],
      lore_document: { blocks: [{ kind: "text", text: "Keeps the light." }] },
    });
  });
});
