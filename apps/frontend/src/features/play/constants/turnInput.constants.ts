// NOTE: Mirrors the server default `turn_action_max_chars` in TRS config. The
// server stays authoritative and truncates anything longer, so a drifted value
// only affects the textarea, never what the narrator receives.
export const TURN_ACTION_MAX_CHARS = 2000;

export const TURN_ACTION_COUNTER_VISIBLE_RATIO = 0.8;
