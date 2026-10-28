// Turn-log text for a timed prompt that ran out with no answer.
export const RULE_CHECK_TIMEOUT_ACTION_TEXT = "(No answer.)";

// Used only when an older server payload carries no hidden_grace_ms.
export const DEFAULT_HIDDEN_GRACE_MS = 1500;

export const TIME_ENTRY_ENTER_OPTION_ID = "enter";
export const TIME_ENTRY_REJECT_OPTION_ID = "reject";
export const DEFAULT_TIME_ENTRY_ENTER_LABEL = "Write it in the Log";
export const DEFAULT_TIME_ENTRY_REJECT_LABEL = "Reject the visitor";

// How long the prompt stays locked after the narration lands, so the last lines
// can be read before the clock starts.
export const READING_WORDS_PER_MINUTE = 250;
export const MIN_READING_BEAT_MS = 2000;
export const MAX_READING_BEAT_MS = 7000;
export const ARM_RETRY_DELAY_MS = 1000;
