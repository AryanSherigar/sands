import { getThematicTag } from "@/shared/constants/thematic-tags";
import { CONTENT_TAG_LABELS } from "@/shared/constants/content-tags";
import type { ContentTag } from "@/shared/constants/content-tags";
import type { SetupInputField } from "@/shared/types/scenario.types";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import {
  ADVANCED_MODE,
  COMPLEXITY_LABELS,
  DICE_CHIP,
  MAP_CHIP,
  MINIGAME_CHIP,
  MATURE_CHIP_EXPLANATION,
  MATURE_CHIP_LABEL,
  MODE_LABELS,
  MULTIPLAYER_CHIP,
  MULTIPLAYER_SUPPORT_VALUES,
} from "../constants/scenarioPage.constants";
import type { MechanicalChipDefinition } from "../constants/scenarioPage.constants";
import type { ScenarioDetailResponse } from "../types/scenario";
import type {
  AgeChip,
  InProgressSummary,
  RatingBucket,
  SetupSummary,
} from "../types/scenarioPage.types";
import type {
  RatingCount,
  ScenarioReviewListResponse,
  ScenarioReviewResponse,
} from "../types/scenario";

export const getPrimaryGenre = (genreTags: string[]): string | null =>
  genreTags[0] ?? null;

export const getModeLabel = (mode: string): string =>
  MODE_LABELS[mode] ?? mode;

export const getComplexityLabel = (tier: string): string =>
  COMPLEXITY_LABELS[tier] ?? tier;

export const getThematicChips = (
  scenario: ScenarioDetailResponse,
): MechanicalChipDefinition[] =>
  (scenario.content_tags ?? []).flatMap((tagId) => {
    const definition = getThematicTag(tagId);
    return definition ? [definition] : [];
  });

export const getMechanicalChips = (
  scenario: ScenarioDetailResponse,
): MechanicalChipDefinition[] => {
  const chips: MechanicalChipDefinition[] = [];
  if (scenario.mode === ADVANCED_MODE) chips.push(DICE_CHIP);
  if (scenario.has_maps) chips.push(MAP_CHIP);
  if (scenario.has_minigames) chips.push(MINIGAME_CHIP);
  if (MULTIPLAYER_SUPPORT_VALUES.includes(scenario.player_count_support)) {
    chips.push(MULTIPLAYER_CHIP);
  }
  return chips;
};

const isContentTag = (value: string | null): value is ContentTag =>
  value !== null && value in CONTENT_TAG_LABELS;

export const isMatureScenario = (scenario: ScenarioDetailResponse): boolean =>
  scenario.is_mature || scenario.content_tag === "mature";

export const getAgeChip = (
  scenario: ScenarioDetailResponse,
): AgeChip | null => {
  if (isMatureScenario(scenario)) {
    return {
      label: MATURE_CHIP_LABEL,
      explanation: MATURE_CHIP_EXPLANATION,
      isMature: true,
    };
  }
  if (!isContentTag(scenario.content_tag)) return null;
  return {
    label: CONTENT_TAG_LABELS[scenario.content_tag],
    explanation: "Suggested audience for this story.",
    isMature: false,
  };
};

export const summarizeInProgress = (
  runs: UserPlaythroughSummary[],
  scenarioId: string,
): InProgressSummary => {
  const activeRuns = runs.filter(
    (run) => run.scenario_id === scenarioId && run.status === "active",
  );
  if (activeRuns.length === 0) return { kind: "none" };
  if (activeRuns.length > 1) {
    return { kind: "multiple", count: activeRuns.length };
  }
  const [run] = activeRuns;
  return {
    kind: "single",
    playthroughId: run.playthrough_id,
    turnCount: run.turn_count,
  };
};

export const formatRatingLabel = (
  average: number,
  reviewCount: number,
): string => {
  if (reviewCount === 0) return "No ratings yet";
  const noun = reviewCount === 1 ? "review" : "reviews";
  return `Rated ${average.toFixed(1)} out of 5 from ${reviewCount} ${noun}`;
};

export const getCreatorInitials = (displayName: string | null): string => {
  const trimmed = displayName?.trim();
  if (!trimmed) return "?";
  return trimmed.slice(0, 2).toUpperCase();
};

export const getSetupSummary = (setupSchema: SetupInputField[]): SetupSummary => {
  const requiredLabels = setupSchema
    .filter((field) => field.required)
    .map((field) => field.label);
  return {
    requiredLabels,
    optionalCount: setupSchema.length - requiredLabels.length,
    isQuickStart: setupSchema.length > 0 && requiredLabels.length === 0,
  };
};

const PERCENT_MULTIPLIER = 100;

export const getRatingBuckets = (
  ratingCounts: RatingCount[],
  totalCount: number,
): RatingBucket[] =>
  [...ratingCounts]
    .sort((first, second) => second.stars - first.stars)
    .map(({ stars, count }) => ({
      stars,
      count,
      percent:
        totalCount === 0 ? 0 : Math.round((count / totalCount) * PERCENT_MULTIPLIER),
    }));

export const withoutReview = (
  reviews: ScenarioReviewResponse[],
  excludedReviewId: string | undefined,
): ScenarioReviewResponse[] =>
  reviews.filter((review) => review.review_id !== excludedReviewId);

const adjustRatingCounts = (
  counts: RatingCount[],
  removedStars: number | null,
  addedStars: number,
): RatingCount[] =>
  counts.map(({ stars, count }) => {
    const removed = stars === removedStars ? 1 : 0;
    const added = stars === addedStars ? 1 : 0;
    return { stars, count: count - removed + added };
  });

const averageFromCounts = (counts: RatingCount[]): number => {
  const total = counts.reduce((sum, { count }) => sum + count, 0);
  if (total === 0) return 0;
  const weighted = counts.reduce((sum, { stars, count }) => sum + stars * count, 0);
  return weighted / total;
};

export const applySubmittedReview = (
  page: ScenarioReviewListResponse,
  submitted: ScenarioReviewResponse,
): ScenarioReviewListResponse => {
  const previousStars = page.own_review?.rating ?? null;
  const ratingCounts = adjustRatingCounts(
    page.rating_counts,
    previousStars,
    submitted.rating,
  );
  return {
    ...page,
    items: withoutReview(page.items, submitted.review_id),
    total_count: page.own_review ? page.total_count : page.total_count + 1,
    average_rating: averageFromCounts(ratingCounts),
    rating_counts: ratingCounts,
    own_review: submitted,
  };
};

export const getEndingsProgressPercent = (
  foundCount: number,
  totalCount: number,
): number =>
  totalCount === 0 ? 0 : Math.round((foundCount / totalCount) * PERCENT_MULTIPLIER);

export const formatEndingDate = (isoTimestamp: string): string =>
  new Date(isoTimestamp).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
