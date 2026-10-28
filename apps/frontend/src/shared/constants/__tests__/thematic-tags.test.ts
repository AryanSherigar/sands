import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  MAX_THEMATIC_TAGS,
  THEMATIC_TAGS,
  getThematicTag,
} from "../thematic-tags";

const BACKEND_VOCABULARY_PATH = resolve(
  process.cwd(),
  "../core-api/app/models/content_tags.py",
);

const readBackendVocabulary = (): string[] => {
  const source = readFileSync(BACKEND_VOCABULARY_PATH, "utf-8");
  const block = /CONTENT_TAG_VOCABULARY[^=]*=\s*\(([\s\S]*?)\)/.exec(source);
  if (!block) throw new Error("CONTENT_TAG_VOCABULARY not found in backend");
  return [...block[1].matchAll(/"([^"]+)"/g)].map((match) => match[1]);
};

const readBackendMax = (): number => {
  const source = readFileSync(BACKEND_VOCABULARY_PATH, "utf-8");
  const match = /MAX_CONTENT_TAGS\s*=\s*(\d+)/.exec(source);
  if (!match) throw new Error("MAX_CONTENT_TAGS not found in backend");
  return Number(match[1]);
};

describe("thematic tag vocabulary", () => {
  it("matches the backend vocabulary exactly, in the same order", () => {
    expect(THEMATIC_TAGS.map((tag) => tag.id)).toEqual(readBackendVocabulary());
  });

  it("uses the same maximum as the backend", () => {
    expect(MAX_THEMATIC_TAGS).toBe(readBackendMax());
  });

  it("gives every tag a label and a one-line explanation", () => {
    for (const tag of THEMATIC_TAGS) {
      expect(tag.label.length).toBeGreaterThan(0);
      expect(tag.explanation.length).toBeGreaterThan(0);
    }
  });

  it("looks tags up by id and returns undefined for unknown ones", () => {
    expect(getThematicTag("romance")?.label).toBe("Romance");
    expect(getThematicTag("nope")).toBeUndefined();
  });
});
