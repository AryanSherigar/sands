// NOTE: Placeholder action_text for a `check_resolution` turn submission —
// TurnRequestInput.action_text is required even though this turn kind
// carries no player-authored narrative text (see play.store.ts's
// submitCheckResolution and docs/specs/master-mode-checks.spec.md).
export const CHECK_RESOLUTION_ACTION_TEXT = "Submitted check resolution.";

// Fixed duration the roll animation plays for, decoupled from network
// timing — a product/feel decision, tunable independently of this file's
// other export. Narration tokens arriving before this elapses are buffered,
// not rendered (see play.store.ts's is_check_animation_pending).
export const CHECK_ROLL_ANIMATION_DURATION_MS = 1800;
