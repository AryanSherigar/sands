export const MAX_CHECK_OPTIONS = 6;
export const MIN_CHECK_OPTIONS = 2;
export const MAX_RECALL_VARIANTS = 5;
export const MIN_RECALL_VARIANTS = 2;
export const MAX_OPTION_MUTATIONS = 8;
export const MIN_WINDOW_MS = 1_000;
export const MAX_WINDOW_MS = 120_000;
export const DEFAULT_TIMED_WINDOW_MS = 12_000;
export const DEFAULT_RECALL_WINDOW_MS = 30_000;
export const GENTLE_WINDOW_WARNING_MS = 3_000;
export const DEFAULT_MAX_REOPENS = 3;
export const MAX_REOPENS = 10;
export const MS_PER_SECOND = 1_000;
export const MAX_VARIANT_LENGTH = 200;
export const HIDDEN_TAB_GRACE_SECONDS = 1.5;

export const RULE_CHECK_KIND_OPTIONS = [
  { value: "timed_choice", label: "Timed choice" },
  { value: "recall", label: "Recall test" },
] as const;

export const TIME_ENTRY_KIND_LABEL = "Time entry";
export const NOT_EDITABLE_KINDS = ["time_entry"] as const;
export const NOT_EDITABLE_NOTE = "This check type isn't editable in the form yet.";
