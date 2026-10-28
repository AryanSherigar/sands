import type {
  FeedbackCategory,
  FlagReason,
} from "../types/alphaFeedback.types";

export const FEEDBACK_BODY_MAX_CHARS = 2000;
export const FLAG_NOTE_MAX_CHARS = 500;
export const LOCAL_TURN_ID_PREFIX = "local-";

export const FEEDBACK_CATEGORIES: ReadonlyArray<{
  value: FeedbackCategory;
  label: string;
}> = [
  { value: "bug", label: "Something broke" },
  { value: "confusing", label: "Confusing" },
  { value: "scary", label: "Scary" },
  { value: "other", label: "Other" },
];

export const FLAG_REASONS: ReadonlyArray<{ value: FlagReason; label: string }> = [
  { value: "broke_rule", label: "Broke a rule" },
  { value: "contradicted", label: "Contradicted earlier text" },
  { value: "out_of_character", label: "Out of character" },
  { value: "too_long", label: "Too long" },
  { value: "other", label: "Other" },
];

export const TENSION_RATINGS = [1, 2, 3, 4, 5] as const;
