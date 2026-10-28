import { describe, expect, it } from "vitest";
import { readSentenceMetadata, toStoredMetadata } from "./sentenceMetadata";

describe("sentenceMetadata", () => {
  it("reads the stored rows and joiner", () => {
    const stored = { rows: [{ comparison: "drops_to" }], joiner: "or" };
    expect(readSentenceMetadata(stored)).toEqual(stored);
  });

  it("returns undefined for anything that is not sentence metadata", () => {
    expect(readSentenceMetadata(null)).toBeUndefined();
    expect(readSentenceMetadata({})).toBeUndefined();
    expect(readSentenceMetadata({ rows: [{ comparison: "sideways" }], joiner: "and" })).toBeUndefined();
    expect(readSentenceMetadata({ rows: [], joiner: "xor" })).toBeUndefined();
  });

  it("keeps unrelated stored keys when writing metadata", () => {
    const written = toStoredMetadata({ rows: [{ comparison: "at_most" }], joiner: "and" }, { placement: "top" });
    expect(written).toEqual({ placement: "top", rows: [{ comparison: "at_most" }], joiner: "and" });
  });

  it("writes null when there is nothing to store", () => {
    expect(toStoredMetadata(undefined)).toBeNull();
  });
});
