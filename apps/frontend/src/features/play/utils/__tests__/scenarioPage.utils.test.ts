import { describe, expect, it } from "vitest";
import type { SetupInputField } from "@/shared/types/scenario.types";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import type {
  ScenarioDetailResponse,
  ScenarioReviewListResponse,
  ScenarioReviewResponse,
} from "../../types/scenario";
import {
  formatRatingLabel,
  getAgeChip,
  getMechanicalChips,
  getRatingBuckets,
  getSetupSummary,
  getThematicChips,
  applySubmittedReview,
  getEndingsProgressPercent,
  summarizeInProgress,
} from "../scenarioPage.utils";

const buildScenario = (
  overrides: Partial<ScenarioDetailResponse> = {},
): ScenarioDetailResponse => ({
  scenario_id: "scenario-1",
  creator_id: "creator-1",
  creator_display_name: "Ayla",
  is_bookmarked: false,
  title: "Story",
  logline: null,
  mode: "newbie",
  status: "published",
  genre_tags: ["Horror"],
  complexity_tier: "newbie",
  player_count_support: "solo",
  estimated_playtime: null,
  playtime_bucket: null,
  is_mature: false,
  cover_image_url: null,
  content_tag: null,
  play_count: 0,
  rating_avg: "0.00",
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const buildRun = (
  overrides: Partial<UserPlaythroughSummary> = {},
): UserPlaythroughSummary => ({
  playthrough_id: "run-1",
  scenario_id: "scenario-1",
  scenario_title: "Story",
  scenario_mode: "newbie",
  cover_image_url: null,
  turn_count: 12,
  status: "active",
  ended_outcome_tag: null,
  ended_outcome_title: null,
  ended_outcome_text: null,
  character_name: null,
  character_archetype: null,
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const buildReview = (
  overrides: Partial<ScenarioReviewResponse> = {},
): ScenarioReviewResponse => ({
  review_id: "review-1",
  scenario_id: "scenario-1",
  user_id: "user-1",
  user_display_name: "Eldrin",
  rating: 5,
  comment: null,
  created_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const buildField = (overrides: Partial<SetupInputField> = {}): SetupInputField => ({
  id: "field-1",
  key: "name",
  label: "Name",
  type: "text",
  required: true,
  options: [],
  ...overrides,
});

describe("summarizeInProgress", () => {
  it("ignores other scenarios and finished runs", () => {
    const runs = [
      buildRun({ scenario_id: "other" }),
      buildRun({ playthrough_id: "run-2", status: "completed" }),
      buildRun({ playthrough_id: "run-3", status: "abandoned" }),
    ];

    expect(summarizeInProgress(runs, "scenario-1")).toEqual({ kind: "none" });
  });

  it("returns the single active run with its turn count", () => {
    expect(summarizeInProgress([buildRun()], "scenario-1")).toEqual({
      kind: "single",
      playthroughId: "run-1",
      turnCount: 12,
    });
  });

  it("returns a count when several runs are active", () => {
    const runs = [buildRun(), buildRun({ playthrough_id: "run-2" })];

    expect(summarizeInProgress(runs, "scenario-1")).toEqual({
      kind: "multiple",
      count: 2,
    });
  });
});

describe("getMechanicalChips", () => {
  it("adds dice for advanced and multiplayer chips, in that order", () => {
    const chips = getMechanicalChips(
      buildScenario({ mode: "master", player_count_support: "both" }),
    );

    expect(chips.map((chip) => chip.id)).toEqual([
      "dice-and-stat-resolution",
      "multiplayer-capable",
    ]);
  });

  it("returns nothing for a simple solo story", () => {
    expect(getMechanicalChips(buildScenario())).toEqual([]);
  });
});

describe("getAgeChip", () => {
  it("prefers the mature chip when the flag or the tag says mature", () => {
    expect(getAgeChip(buildScenario({ is_mature: true }))?.isMature).toBe(true);
    expect(getAgeChip(buildScenario({ content_tag: "mature" }))?.isMature).toBe(
      true,
    );
  });

  it("labels a known age rating and skips unknown or missing ones", () => {
    expect(getAgeChip(buildScenario({ content_tag: "teen" }))?.label).toBe("Teen");
    expect(getAgeChip(buildScenario({ content_tag: "PG-13" }))).toBeNull();
    expect(getAgeChip(buildScenario())).toBeNull();
  });
});

describe("getSetupSummary", () => {
  it("lists required labels and counts optional fields", () => {
    const summary = getSetupSummary([
      buildField(),
      buildField({ id: "f2", label: "Class" }),
      buildField({ id: "f3", label: "Item", required: false }),
    ]);

    expect(summary).toEqual({
      requiredLabels: ["Name", "Class"],
      optionalCount: 1,
      isQuickStart: false,
    });
  });

  it("flags a quick start only when fields exist and none are required", () => {
    expect(getSetupSummary([buildField({ required: false })]).isQuickStart).toBe(
      true,
    );
    expect(getSetupSummary([]).isQuickStart).toBe(false);
  });
});

describe("getThematicChips", () => {
  it("returns creator-picked tags in the chosen order", () => {
    const chips = getThematicChips(
      buildScenario({ content_tags: ["moral-ambiguity", "noir-atmosphere"] }),
    );

    expect(chips.map((chip) => chip.label)).toEqual([
      "Moral ambiguity",
      "Noir atmosphere",
    ]);
  });

  it("skips ids no longer in the vocabulary and tolerates a missing field", () => {
    expect(
      getThematicChips(buildScenario({ content_tags: ["retired", "romance"] })).map(
        (chip) => chip.id,
      ),
    ).toEqual(["romance"]);
    expect(getThematicChips(buildScenario())).toEqual([]);
  });
});

describe("getMechanicalChips order", () => {
  it("lists dice, map, minigames, then multiplayer", () => {
    const chips = getMechanicalChips(
      buildScenario({
        mode: "master",
        has_maps: true,
        has_minigames: true,
        player_count_support: "multiplayer",
      }),
    );

    expect(chips.map((chip) => chip.id)).toEqual([
      "dice-and-stat-resolution",
      "map-exploration",
      "minigames",
      "multiplayer-capable",
    ]);
  });
});

const COUNTS = [
  { stars: 1, count: 1 },
  { stars: 5, count: 2 },
  { stars: 4, count: 1 },
  { stars: 3, count: 0 },
  { stars: 2, count: 0 },
];

describe("ratings", () => {
  it("builds descending buckets with percentages of ALL reviews", () => {
    const buckets = getRatingBuckets(COUNTS, 4);

    expect(buckets.map((bucket) => bucket.stars)).toEqual([5, 4, 3, 2, 1]);
    expect(buckets[0]).toEqual({ stars: 5, count: 2, percent: 50 });
    expect(buckets[2].percent).toBe(0);
  });

  it("returns zero percentages with no reviews", () => {
    const empty = COUNTS.map(({ stars }) => ({ stars, count: 0 }));

    expect(getRatingBuckets(empty, 0).every((bucket) => bucket.percent === 0)).toBe(
      true,
    );
  });

  it("writes the rating as text, not stars", () => {
    expect(formatRatingLabel(4.6, 132)).toBe("Rated 4.6 out of 5 from 132 reviews");
    expect(formatRatingLabel(5, 1)).toBe("Rated 5.0 out of 5 from 1 review");
    expect(formatRatingLabel(0, 0)).toBe("No ratings yet");
  });
});

describe("applySubmittedReview", () => {
  const buildPage = (
    overrides: Partial<ScenarioReviewListResponse> = {},
  ): ScenarioReviewListResponse => ({
    items: [buildReview({ review_id: "other", user_id: "other" })],
    total_count: 4,
    average_rating: 3.75,
    rating_counts: COUNTS,
    own_review: null,
    ...overrides,
  });

  it("adds a first-time review to the totals, counts and average", () => {
    const submitted = buildReview({ review_id: "mine", user_id: "me", rating: 3 });

    const result = applySubmittedReview(buildPage(), submitted);

    expect(result.total_count).toBe(5);
    expect(result.own_review).toBe(submitted);
    expect(result.rating_counts.find((c) => c.stars === 3)?.count).toBe(1);
    expect(result.average_rating).toBeCloseTo(18 / 5);
  });

  it("moves an edited review between buckets without changing the total", () => {
    const previous = buildReview({ review_id: "mine", user_id: "me", rating: 1 });
    const edited = { ...previous, rating: 5 };

    const result = applySubmittedReview(buildPage({ own_review: previous }), edited);

    expect(result.total_count).toBe(4);
    expect(result.rating_counts.find((c) => c.stars === 1)?.count).toBe(0);
    expect(result.rating_counts.find((c) => c.stars === 5)?.count).toBe(3);
  });

  it("drops the submitted review from the paged items to avoid a duplicate", () => {
    const submitted = buildReview({ review_id: "other", user_id: "other" });

    const result = applySubmittedReview(buildPage(), submitted);

    expect(result.items).toEqual([]);
  });
});

describe("getEndingsProgressPercent", () => {
  it("rounds found over total to a whole percent", () => {
    expect(getEndingsProgressPercent(2, 5)).toBe(40);
    expect(getEndingsProgressPercent(1, 3)).toBe(33);
  });

  it("is zero when there are no endings", () => {
    expect(getEndingsProgressPercent(0, 0)).toBe(0);
  });
});
