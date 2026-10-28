import { describe, expect, it } from "vitest";
import {
  buildLinkViews,
  describeLink,
  findPickBlockIndex,
  findPickFact,
  getLinkSuggestions,
  getLinksForEntity,
} from "./cardLinks";
import { buildEntityFixture, buildFactFixture } from "../test/cardApiMock";
import type { QuestionGroup } from "../types/guide.types";

const mara = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
const lighthouse = buildEntityFixture({
  entity_id: "lighthouse",
  canonical_name: "The Lighthouse",
  entity_type: "location",
});
const livesIn = buildFactFixture({
  fact_id: "f1",
  subject_entity_id: "mara",
  predicate: "lives in",
  object_entity_id: "lighthouse",
});
const literalFact = buildFactFixture({
  fact_id: "f2",
  subject_entity_id: "mara",
  predicate: "age",
  object_entity_id: null,
  object_literal: "40",
});

const QUESTIONS: QuestionGroup[] = [
  {
    id: "where",
    name: "Where",
    questions: [
      {
        id: "found-at",
        label: "Found at",
        prompt: "Where?",
        pick: { kind: "place", predicate: "is usually found at" },
      },
    ],
  },
];

describe("cardLinks", () => {
  it("getLinksForEntity returns entity-to-entity links from either side", () => {
    const facts = [livesIn, literalFact];

    expect(getLinksForEntity(facts, "mara")).toEqual([livesIn]);
    expect(getLinksForEntity(facts, "lighthouse")).toEqual([livesIn]);
    expect(getLinksForEntity(facts, "other")).toEqual([]);
  });

  it("getLinkSuggestions follows the type pair", () => {
    expect(getLinkSuggestions("character", "place")).toContain("lives in");
    expect(getLinkSuggestions("place", "place")).toContain("is next to");
    expect(getLinkSuggestions("thing", "place")).toContain("is hidden in");
  });

  it("getLinkSuggestions falls back to a generic suggestion", () => {
    expect(getLinkSuggestions("group", "thing").length).toBeGreaterThan(0);
  });

  it("findPickFact prefers the exact predicate, then any link to the target", () => {
    const pickFact = buildFactFixture({
      fact_id: "f3",
      subject_entity_id: "mara",
      predicate: "is usually found at",
      object_entity_id: "lighthouse",
    });

    const exact = findPickFact([livesIn, pickFact], "mara", [mara, lighthouse], {
      predicate: "is usually found at",
      pickedName: "The Lighthouse",
    });
    const fallback = findPickFact([livesIn], "mara", [mara, lighthouse], {
      predicate: "is usually found at",
      pickedName: "The Lighthouse",
    });

    expect(exact?.fact_id).toBe("f3");
    expect(fallback?.fact_id).toBe("f1");
  });

  it("findPickBlockIndex finds the block a link belongs to", () => {
    const document = {
      blocks: [
        { kind: "text" as const, text: "x" },
        {
          kind: "answer" as const,
          question_id: "found-at",
          label: "Found at",
          text: "The Lighthouse",
        },
      ],
    };

    expect(
      findPickBlockIndex(document, QUESTIONS, "is usually found at", "The Lighthouse"),
    ).toBe(1);
    expect(findPickBlockIndex(document, QUESTIONS, "lives in", "The Lighthouse")).toBe(-1);
  });
});

describe("buildLinkViews", () => {
  it("resolves both ends of each link and describes it as a sentence", () => {
    const views = buildLinkViews([livesIn], [mara, lighthouse], "mara");

    expect(views).toHaveLength(1);
    expect(views[0].subject?.canonical_name).toBe("Mara");
    expect(describeLink(views[0])).toBe("Mara lives in The Lighthouse");
  });

  it("marks an end that no longer exists as a missing card", () => {
    const [view] = buildLinkViews([livesIn], [mara], "mara");

    expect(describeLink(view)).toBe("Mara lives in Missing card");
  });
});
