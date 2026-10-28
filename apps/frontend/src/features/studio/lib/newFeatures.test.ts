import { describe, expect, it } from "vitest";
import { NEW_FEATURES, type NewFeature } from "../constants/newFeatures";
import {
  addSeenFeature,
  formatReleaseDate,
  getFeatureById,
  getFeaturesReleasedAfter,
  splitFeaturesBySeen,
} from "./newFeatures";

const feature = (id: string, releasedOn: string): NewFeature => ({
  id,
  name: id,
  description: "",
  releasedOn,
  location: "",
  example: "",
  isAdvanced: false,
  target: { kind: "card" },
});

describe("new features registry", () => {
  it("ships the six launch entries and the six Advanced mode entries", () => {
    expect(NEW_FEATURES.map((entry) => entry.name)).toEqual([
      "Triggers",
      "Links",
      "Always remember",
      "Storytelling style",
      "Player step",
      "Questions to Help",
      "Advanced mode",
      "Endings",
      "Tracked values",
      "Rules",
      "Hard limits",
      "Card values",
    ]);
    expect(new Set(NEW_FEATURES.map((entry) => entry.id)).size).toBe(12);
    expect(NEW_FEATURES.slice(6).every((entry) => entry.isAdvanced)).toBe(true);
  });

  it("finds an entry by id", () => {
    expect(getFeatureById("links")?.name).toBe("Links");
    expect(getFeatureById("missing")).toBeNull();
  });
});

describe("getFeaturesReleasedAfter", () => {
  const registry = [feature("old", "2026-11-10"), feature("new", "2026-11-20")];

  it("keeps only features released after the story was created", () => {
    expect(getFeaturesReleasedAfter("2026-11-15T10:00:00Z", registry).map((entry) => entry.id)).toEqual(["new"]);
    expect(getFeaturesReleasedAfter("2026-12-01T10:00:00Z", registry)).toEqual([]);
    expect(getFeaturesReleasedAfter("2026-10-27T10:00:00Z", registry)).toHaveLength(2);
  });
});

describe("seen state", () => {
  it("splits eligible features into unseen and seen", () => {
    const eligible = [feature("a", "2026-11-20"), feature("b", "2026-11-20")];
    const groups = splitFeaturesBySeen(eligible, ["b"]);
    expect(groups.unseen.map((entry) => entry.id)).toEqual(["a"]);
    expect(groups.seen.map((entry) => entry.id)).toEqual(["b"]);
  });

  it("adds a seen id once", () => {
    expect(addSeenFeature(["a"], "b")).toEqual(["a", "b"]);
    expect(addSeenFeature(["a"], "a")).toEqual(["a"]);
  });

  it("formats the release date without shifting the day", () => {
    expect(formatReleaseDate("2026-11-20")).toBe("Nov 20, 2026");
  });
});
