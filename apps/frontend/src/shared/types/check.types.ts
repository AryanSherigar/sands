// Master-mode dice-check shapes, shared between play/ and its store —
// mirrors minigame.types.ts's boundary rule: the roll is always computed
// and validated server-side, never client-supplied. See
// docs/specs/master-mode-checks.spec.md.

type CheckResolution = "attempt" | "decline";

// The play-time payload delivered via the "check" SSE event when the
// narrator proposes a check — no roll yet.
export interface CheckEventPayload {
  check_id: string;
  check_type: string;
  difficulty_class: number;
  reasoning?: string | null;
}

// Raw shape of state._pending_check, read on load/reload — same fields as
// CheckEventPayload plus the roll, present only once ensure_roll_persisted
// has run (see PlaythroughData.pending_check's reload-resume behaviour).
export interface PendingCheckState extends CheckEventPayload {
  resolved_roll: number | null;
}

export interface CheckResolutionPayload {
  check_id: string;
  resolution: CheckResolution;
}

// The play-time payload delivered via the "check_resolved" SSE event,
// immediately after the early roll commit (attempt) or right after
// accepting a decline — before narration.
export interface CheckResolvedPayload {
  check_id: string;
  check_type: string;
  difficulty_class: number;
  resolved_roll: number | null;
  is_success: boolean | null;
}

// --- Rule checks (tool `rule_checks`): timed prompts the server opens from
// state. The client only reports which option it chose or that its timer ran
// out; the server judges lateness and decides the result.

export type RuleCheckKind = "timed_choice" | "recall" | "time_entry";

const RULE_CHECK_KINDS: readonly RuleCheckKind[] = [
  "timed_choice",
  "recall",
  "time_entry",
];

export interface RuleCheckOptionView {
  id: string;
  label: string;
}

// One recall variant as shown to the player: the id encodes the original index
// and which one is correct never leaves the server.
interface RuleCheckVariantView {
  id: string;
  text: string;
}

// The "check" SSE event for kind != dice, and the public part of
// state._pending_check. Never carries results, mutations or timeout outcomes.
export interface RuleCheckEventPayload {
  check_id: string;
  kind: RuleCheckKind;
  prompt: string;
  options: RuleCheckOptionView[];
  variants?: RuleCheckVariantView[];
  window_ms: number;
  issued_at: number;
  hidden_grace_ms?: number;
  reopen_count?: number;
  // False until the server starts the prompt's clock (after the player has had
  // time to read the narration). Absent on checks stamped before arming existed,
  // which count as armed.
  is_armed?: boolean;
  // The server clock when the event was sent (absent from state._pending_check):
  // the prompt's window is stamped before media and commit, so this is what lets
  // the client start the countdown with the time that is really left.
  server_time_ms?: number;
  told_label?: string | null;
  wall_label?: string | null;
  wall_minute_of_day?: number | null;
}

// POST /v1/turn/rule-check/arm: the window the server just started.
export interface RuleCheckArmedPayload {
  check_id: string;
  issued_at: number;
  window_ms: number;
  server_time_ms: number;
}

export const isRuleCheckArmed = (check: RuleCheckEventPayload): boolean =>
  check.is_armed !== false;

// The "check_resolved" SSE event for a rule check: id and kind only.
export interface RuleCheckResolvedPayload {
  check_id: string;
  kind: RuleCheckKind;
}

export interface CheckReportPayload {
  check_id: string;
  choice_id?: string;
  entry_text?: string;
  timed_out?: boolean;
  was_hidden?: boolean;
  is_untimed?: boolean;
}

// A rule check on screen, with the time left when it became active so the
// countdown survives re-renders and reloads.
export interface ActiveRuleCheck extends RuleCheckEventPayload {
  initial_remaining_ms: number;
  started_at_client_ms: number;
}

export const isRuleCheckKind = (value: unknown): value is RuleCheckKind =>
  RULE_CHECK_KINDS.some((kind) => kind === value);

export const isRuleCheckPayload = (
  raw: unknown,
): raw is RuleCheckEventPayload =>
  typeof raw === "object" &&
  raw !== null &&
  isRuleCheckKind((raw as { kind?: unknown }).kind);
