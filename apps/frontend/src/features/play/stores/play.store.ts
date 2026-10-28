import { create } from "zustand";
import {
  ActionMode,
  ChapterDelta,
  EBookTheme,
  InputTruncatedPayload,
  MemoryDegradedPayload,
  PlaythroughData,
  PlaythroughEndedPayload,
  TurnLogItem,
} from "../types/play.types";
import { TurnSummaryEventPayload } from "../types/turnSummary.types";
import { mapTurnSummaryEvent } from "../utils/chapterDelta";
import { createPostSSEConnection, SSEHandlers } from "@/shared/lib/sse-client";
import { isAlphaPausedError } from "@/shared/lib/alpha-paused-error";
import { isRateLimitError } from "@/shared/lib/rate-limit-error";
import type { QuotaNoticePayload } from "@/shared/types/rateLimit.types";
import {
  generateClientActionId,
  generateRequestId,
  setCurrentRequestId,
} from "@/shared/lib/request-id";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { queryClient } from "@/shared/lib/query-client";
import { ScenarioMood } from "@/shared/types/audio.types";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { narrationPlayback } from "@/shared/lib/audio/narration-playback";
import { getMoodTrackUrl } from "@/shared/constants/audio";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { ReaderFontSize } from "@/shared/types/readerPreferences.types";
import { isVoiceOutputRequested } from "../lib/voiceOutputRequest";
import {
  MinigameEventPayload,
  MinigameResultPayload,
} from "@/shared/types/minigame.types";
import {
  ActiveRuleCheck,
  CheckEventPayload,
  CheckReportPayload,
  CheckResolutionPayload,
  CheckResolvedPayload,
  PendingCheckState,
  RuleCheckResolvedPayload,
  isRuleCheckArmed,
  isRuleCheckKind,
  isRuleCheckPayload,
} from "@/shared/types/check.types";
import { minigameActionText } from "../lib/minigameActionText";
import { parseClientEffect } from "@/shared/lib/client-effects/parseClientEffect";
import type { ClientEffect } from "@/shared/lib/client-effects/clientEffects.types";
import { CHECK_RESOLUTION_ACTION_TEXT } from "../constants/check.constants";
import { getPlaythrough } from "@/shared/api/playthroughs.api";
import { armRuleCheck } from "../api/ruleCheck.api";
import { toActiveRuleCheck } from "../utils/ruleCheckTiming";
import {
  handleRuleRevealed,
  handleSensoryCue,
  shouldIgnoreNarratorMood,
} from "../lib/atmosphereSubscriber";
import { hasNewlyRevealedRule } from "../utils/ruleSheetChanges";
import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import { isSensoryCueId } from "@/shared/constants/sensory-cues";
import { logEvent } from "@/shared/lib/logger";
import {
  emitTurnRetry,
  nextTurnNumber,
  startTurnStreamTelemetry,
} from "../lib/turnStreamTelemetry";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";

// The POST /v1/turn body shared by a normal narrative action, a minigame
// result submission, and a check resolution (TurnRequestInput on the TRS
// side — app/models/turn.py).
interface TurnStreamBody {
  playthrough_id: string;
  participant_id: string;
  client_action_id: string;
  action_text: string;
  action_kind:
    | "narrative"
    | "minigame_result"
    | "check_resolution"
    | "check_report";
  action_mode: ActionMode;
  minigame_result?: MinigameResultPayload;
  check_resolution?: CheckResolutionPayload;
  check_report?: CheckReportPayload;
  voice_output_requested: boolean;
}

// Buffered terminal event for a check-resolution "attempt" turn — held
// until the fixed-duration roll animation finishes (see
// is_check_animation_pending), then replayed by revealCheckAnimation.
interface CheckTerminalPending {
  kind: "done" | "degraded";
  actionText: string;
  message: string;
  turnId?: string;
}

type MinigameResultStatus =
  "reconciling" | "submitting" | "retryable" | "terminal";

interface PendingMinigameResult {
  result: MinigameResultPayload;
  // The player-facing line sent as the turn's action, reused by every retry.
  action_text: string;
  // Reused by every retry of this same result, so a retry after a lost "done"
  // replays the committed turn instead of creating a second one.
  client_action_id: string;
  attempts: number;
  status: MinigameResultStatus;
  fallback_used: boolean;
}

const MAX_MINIGAME_RESULT_ATTEMPTS = 3;

interface EffectQueue {
  pending_client_effects: ClientEffect[];
  queued_client_effects: ClientEffect[];
  active_client_effect: ClientEffect | null;
}

function queueCommittedEffects(state: EffectQueue): EffectQueue {
  const waiting = [...state.queued_client_effects, ...state.pending_client_effects];
  const active = state.active_client_effect ?? waiting[0] ?? null;
  const queued = state.active_client_effect ? waiting : waiting.slice(1);
  return {
    pending_client_effects: [],
    queued_client_effects: queued,
    active_client_effect: active,
  };
}

function parseDoneTurnId(data: string): string | undefined {
  if (!data) return undefined;
  try {
    const parsed: unknown = JSON.parse(data);
    if (typeof parsed !== "object" || parsed === null) return undefined;
    const turnId = (parsed as { turn_id?: unknown }).turn_id;
    return typeof turnId === "string" ? turnId : undefined;
  } catch (error: unknown) {
    console.warn("Malformed done event payload", error);
    return undefined;
  }
}

function pendingMinigameFromServer(
  state: Record<string, unknown>,
): MinigameEventPayload | null {
  const pending = state._pending_minigame;
  if (!pending || typeof pending !== "object") return null;
  const payload = pending as Partial<MinigameEventPayload>;
  return typeof payload.minigame_id === "string"
    ? (payload as MinigameEventPayload)
    : null;
}

function isSamePendingAttempt(
  pending: MinigameEventPayload | null,
  result: MinigameResultPayload,
): boolean {
  if (!pending || pending.minigame_id !== result.minigame_id) return false;
  // Pending records written before attempt ids deliberately remain replayable.
  return !pending.attempt_id || pending.attempt_id === result.attempt_id;
}

interface PlayStoreState {
  playthrough: PlaythroughData | null;
  active_mode: ActionMode;
  ebook_theme: EBookTheme;
  is_left_sidebar_open: boolean;
  is_right_sidebar_open: boolean;
  is_action_drawer_open: boolean;
  is_chronicle_modal_open: boolean;
  is_rules_panel_hidden: boolean;
  is_narrating: boolean;
  is_turn_paused: boolean;
  streaming_text: string;
  last_submitted_action: string;
  // The client_action_id of the last narrative submission, kept only until it
  // commits: retrying a turn that may have saved must reuse it.
  last_client_action_id: string | null;
  // The action whose cues the player has already heard, and the stream attempt
  // that played them: a retry of that action must not replay them, but a second
  // cue within the same attempt still plays.
  cue_played_action_id: string | null;
  cue_played_generation: number;
  // Client effects (input takeover, phone echo) arrive during a turn's intake
  // and are held until the turn commits, then played one at a time. A retry
  // of the same action must not queue them twice (same rule as cues).
  pending_client_effects: ClientEffect[];
  queued_client_effects: ClientEffect[];
  active_client_effect: ClientEffect | null;
  effects_action_id: string | null;
  effects_generation: number;
  degraded_message: string | null;
  // Set when a `quota_notice` SSE event says this turn skipped its scene
  // image or voice narration because that daily quota is spent. The turn
  // itself still commits normally.
  quota_notice_message: string | null;
  // Set when an `input_truncated` SSE event says the submitted action was cut
  // to the server's size cap. The turn still runs on the truncated text.
  input_truncated_message: string | null;
  // Reasons from the last `memory_degraded` SSE event, or the result of a
  // "Retry memory" call. Empty means memory is keeping up. Cleared by the next
  // turn that finishes without the event.
  memory_degraded_reasons: string[];
  cancel_stream_fn: (() => void) | null;
  // Monotonic ownership token: callbacks from a cancelled/replaced SSE
  // connection must never overwrite newer play state.
  stream_generation: number;
  // Master mode: set when a `turn_summary` SSE event arrives, held until the
  // in-flight turn commits so the chapter summary strip only ever renders
  // from a turn already in playthrough.turns (never mid-stream).
  pending_chapter_delta: ChapterDelta | null;
  // Master mode: set when a `minigame` SSE event arrives, held until the
  // in-flight turn commits — mirrors pending_chapter_delta exactly — so the
  // overlay only ever appears once the triggering turn is fully committed.
  pending_minigame_trigger: MinigameEventPayload | null;
  // Master mode: set when a `playthrough_ended` SSE event arrives, held
  // until the in-flight turn commits — mirrors pending_chapter_delta exactly
  // — so the ending only ever renders once the triggering turn is committed.
  pending_playthrough_ended: PlaythroughEndedPayload | null;
  // Set when a `scene_image` SSE event arrives for a "see" action turn, held
  // until the in-flight turn commits — mirrors pending_chapter_delta exactly.
  pending_scene_image_url: string | null;
  // Set when a `narration_audio` SSE event arrives for a turn that requested
  // voice output, held until the in-flight turn commits — mirrors
  // pending_scene_image_url exactly.
  pending_audio_url: string | null;
  // Which committed turn's narration audio is currently playing, mirrored
  // from the narrationPlayback singleton (see the sync listener at the
  // bottom of this file) — same pattern as active_mood/ambientSoundtrack.
  playing_audio_turn_id: string | null;
  // The minigame currently taking over the play surface full-screen, or one
  // resumed on reload from PlaythroughData.pending_minigame. Null renders
  // nothing (MinigameOverlay is an unconditional, guarded no-op mount).
  active_minigame: MinigameEventPayload | null;
  // Kept until the server's terminal "done" event confirms the pending
  // encounter was consumed. This makes failed submissions recoverable.
  pending_minigame_result: PendingMinigameResult | null;
  // Master mode: set when a `check` SSE event arrives, held until the
  // in-flight turn commits — mirrors pending_minigame_trigger exactly.
  // resolved_roll is always null here (a freshly-proposed check never has
  // one yet) — typed as PendingCheckState only so it assigns directly onto
  // active_check on commit, same shape reload-resume already produces.
  pending_check_trigger: PendingCheckState | null;
  // The check currently gating the play surface (roll/decline prompt), or
  // one resumed on reload from PlaythroughData.pending_check. Null renders
  // nothing (CheckPromptOverlay is an unconditional, guarded no-op mount).
  active_check: PendingCheckState | null;
  // True from the instant "attempt" is submitted until the fixed-duration
  // roll animation completes — decoupled from network timing. While true,
  // incoming narration is buffered (buffered_check_narration) rather than
  // rendered, and the turn's terminal event is held (check_terminal_pending)
  // rather than committed/degraded immediately.
  is_check_animation_pending: boolean;
  buffered_check_narration: string;
  check_terminal_pending: CheckTerminalPending | null;
  // Set the instant the `check_resolved` SSE event arrives — the roll
  // itself, revealed by the UI only once is_check_animation_pending is false.
  resolved_check_outcome: CheckResolvedPayload | null;
  // Rule checks (timed prompts): a `check` event with a rule-check kind is
  // buffered here until the turn commits, then promoted to active_rule_check,
  // the prompt on screen (also resumed on reload from
  // PlaythroughData.pending_rule_check). is_rule_check_submitting is true from
  // the moment an answer is sent until the turn commits or fails.
  pending_rule_check_trigger: ActiveRuleCheck | null;
  active_rule_check: ActiveRuleCheck | null;
  is_rule_check_submitting: boolean;
  // The answer sent for the rule check currently being resolved, kept until the
  // turn commits so Retry re-sends it as a report instead of free text (which
  // the server refuses while a check is open).
  last_check_report: { report: CheckReportPayload; label: string } | null;
  // The id of the last rule check the server resolved. A refetch that was
  // already in flight when it resolved still reports it as open, and must not
  // bring its prompt back.
  last_closed_rule_check_id: string | null;
  reader_font_override: string | null;
  reader_font_size: ReaderFontSize;

  // Actions
  setPlaythrough: (data: PlaythroughData) => void;
  setReaderFontOverride: (fontId: string | null) => void;
  setActiveMode: (mode: ActionMode) => void;
  setEBookTheme: (theme: EBookTheme) => void;
  toggleEBookTheme: () => void;
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  setLeftSidebarOpen: (isOpen: boolean) => void;
  setRightSidebarOpen: (isOpen: boolean) => void;
  openActionDrawer: () => void;
  closeActionDrawer: () => void;
  toggleActionDrawer: () => void;
  openChronicleModal: () => void;
  setRulesPanelHidden: (isHidden: boolean) => void;
  closeChronicleModal: () => void;
  submitTurn: (actionText: string, clientActionId?: string) => void;
  submitMinigameResult: (result: MinigameResultPayload) => void;
  retryMinigameResult: () => void;
  submitMinigameTimeoutFallback: () => void;
  clearActiveMinigame: () => void;
  finishClientEffect: () => void;
  submitCheckResolution: (resolution: CheckResolutionPayload) => void;
  submitCheckReport: (report: CheckReportPayload, actionLabel: string) => void;
  armRuleCheck: (checkId: string) => Promise<void>;
  revealCheckAnimation: () => void;
  continueTurn: () => void;
  stopGeneration: () => void;
  retryLastTurn: () => void;
  clearDegradedMessage: () => void;
  clearQuotaNoticeMessage: () => void;
  clearInputTruncatedMessage: () => void;
  setMemoryDegradedReasons: (reasons: string[]) => void;
  active_mood: ScenarioMood;
  audio_volume: number;
  is_audio_muted: boolean;
  setAudioVolume: (volume: number) => void;
  toggleAudioMute: () => void;
  setMood: (mood: ScenarioMood) => void;
  playTurnAudio: (turnId: string, url: string) => void;
  stopTurnAudio: () => void;

  // Internal — not part of the public store surface; other files should not
  // call these directly. Exposed on the interface only because Zustand
  // actions call each other through get(), which requires them typed here.
  _startTurnStream: (body: TurnStreamBody, actionTextForLog: string) => void;
  _commitStreamedTurn: (actionText: string, turnId?: string) => void;
  _resendCheckReport: (report: CheckReportPayload, label: string) => void;
  _degradeCurrentTurn: (message: string) => void;
}

export const usePlayStore = create<PlayStoreState>((set, get) => ({
  playthrough: null,
  active_mode: "do",
  ebook_theme: useReaderPreferencesStore.getState().theme,
  is_left_sidebar_open: true,
  is_right_sidebar_open: true,
  is_action_drawer_open: false,
  is_chronicle_modal_open: false,
  is_rules_panel_hidden: false,
  is_narrating: false,
  is_turn_paused: false,
  streaming_text: "",
  last_submitted_action: "",
  last_client_action_id: null,
  cue_played_action_id: null,
  cue_played_generation: 0,
  pending_client_effects: [],
  queued_client_effects: [],
  active_client_effect: null,
  effects_action_id: null,
  effects_generation: 0,
  degraded_message: null,
  quota_notice_message: null,
  input_truncated_message: null,
  memory_degraded_reasons: [],
  cancel_stream_fn: null,
  stream_generation: 0,
  pending_chapter_delta: null,
  pending_minigame_trigger: null,
  pending_playthrough_ended: null,
  pending_scene_image_url: null,
  pending_audio_url: null,
  playing_audio_turn_id: narrationPlayback.getPlayingTurnId(),
  active_minigame: null,
  pending_minigame_result: null,
  pending_check_trigger: null,
  active_check: null,
  is_check_animation_pending: false,
  buffered_check_narration: "",
  check_terminal_pending: null,
  resolved_check_outcome: null,
  pending_rule_check_trigger: null,
  active_rule_check: null,
  is_rule_check_submitting: false,
  last_check_report: null,
  last_closed_rule_check_id: null,
  reader_font_override: useReaderPreferencesStore.getState().fontId,
  reader_font_size: useReaderPreferencesStore.getState().fontSize,
  active_mood: "peaceful",
  audio_volume: ambientSoundtrack.getVolume(),
  is_audio_muted: ambientSoundtrack.getIsMuted(),

  setReaderFontOverride: (fontId: string | null) => {
    useReaderPreferencesStore.getState().setFontId(fontId);
    set({ reader_font_override: fontId });
  },

  setPlaythrough: (data: PlaythroughData) => {
    const prevPlaythrough = get().playthrough;
    const isNewPlaythrough =
      !prevPlaythrough ||
      prevPlaythrough.playthrough_id !== data.playthrough_id;
    set({ playthrough: data });

    if (isNewPlaythrough) {
      set({
        pending_client_effects: [],
        queued_client_effects: [],
        active_client_effect: null,
        effects_action_id: null,
      });
      const initialMood = data.initial_mood || "peaceful";
      const trackUrl = getMoodTrackUrl(initialMood, data.music_tracks);
      ambientSoundtrack.transitionTo(initialMood, trackUrl, true);
      // Resume a minigame the player left mid-resolution — reload must not
      // require a fresh SSE "minigame" event to show the overlay again.
    }
    // The API snapshot is authoritative. In particular, this reconciles an
    // ambiguous network failure: if the server consumed the result, dismiss
    // the retained local result; otherwise restore the unresolved encounter.
    if (data.pending_minigame) {
      set({ active_minigame: data.pending_minigame });
    } else {
      set({ active_minigame: null, pending_minigame_result: null });
    }
    // Resume a check the player left mid-resolution — same reload pattern
    // as pending_minigame above. If resolved_roll is already set, the die
    // was cast before the player left; the overlay shows that roll directly
    // rather than replaying the animation (see CheckPromptOverlay).
    if (data.pending_check) {
      set({ active_check: data.pending_check });
    } else {
      set({ active_check: null });
    }
    // Resume a timed prompt the player left open; the same check already on
    // screen keeps its running countdown rather than restarting it.
    const running = get().active_rule_check;
    const isAlreadyClosed =
      data.pending_rule_check?.check_id === get().last_closed_rule_check_id;
    if (!data.pending_rule_check || isAlreadyClosed) {
      set({ active_rule_check: null });
    } else if (running?.check_id !== data.pending_rule_check.check_id) {
      set({
        active_rule_check: toActiveRuleCheck(
          data.pending_rule_check,
          data.server_time_ms,
          Date.now(),
        ),
      });
    }
  },
  setAudioVolume: (vol: number) => {
    ambientSoundtrack.setVolume(vol);
    set({ audio_volume: ambientSoundtrack.getVolume() });
  },
  toggleAudioMute: () => {
    const isMuted = ambientSoundtrack.toggleMute();
    set({ is_audio_muted: isMuted });
  },
  setMood: (mood: ScenarioMood) => {
    const trackUrl = getMoodTrackUrl(mood, get().playthrough?.music_tracks);
    ambientSoundtrack.transitionTo(mood, trackUrl, true);
  },
  playTurnAudio: (turnId: string, url: string) =>
    narrationPlayback.play(turnId, url),
  stopTurnAudio: () => narrationPlayback.stop(),
  setActiveMode: (mode: ActionMode) => set({ active_mode: mode }),
  setEBookTheme: (theme: EBookTheme) => {
    useReaderPreferencesStore.getState().setTheme(theme);
    set({ ebook_theme: theme });
  },
  toggleEBookTheme: () =>
    get().setEBookTheme(
      get().ebook_theme === "dark-velvet" ? "antique-sepia" : "dark-velvet",
    ),
  toggleLeftSidebar: () =>
    set((s) => ({ is_left_sidebar_open: !s.is_left_sidebar_open })),
  toggleRightSidebar: () =>
    set((s) => ({ is_right_sidebar_open: !s.is_right_sidebar_open })),
  setLeftSidebarOpen: (isOpen: boolean) =>
    set({ is_left_sidebar_open: isOpen }),
  setRightSidebarOpen: (isOpen: boolean) =>
    set({ is_right_sidebar_open: isOpen }),
  openActionDrawer: () => set({ is_action_drawer_open: true }),
  closeActionDrawer: () => set({ is_action_drawer_open: false }),
  toggleActionDrawer: () =>
    set((s) => ({ is_action_drawer_open: !s.is_action_drawer_open })),
  openChronicleModal: () => set({ is_chronicle_modal_open: true }),
  setRulesPanelHidden: (isHidden) => set({ is_rules_panel_hidden: isHidden }),
  closeChronicleModal: () => set({ is_chronicle_modal_open: false }),
  clearDegradedMessage: () => set({ degraded_message: null }),
  clearQuotaNoticeMessage: () => set({ quota_notice_message: null }),
  clearInputTruncatedMessage: () => set({ input_truncated_message: null }),
  setMemoryDegradedReasons: (reasons: string[]) =>
    set({ memory_degraded_reasons: reasons }),

  continueTurn: () => {
    const { playthrough, is_narrating, submitTurn } = get();
    if (!playthrough || is_narrating || playthrough.is_spectator) return;
    if (playthrough.ended_outcome_tag) return;
    submitTurn("Continue the story.");
  },

  submitTurn: (actionText: string, clientActionId?: string) => {
    const {
      playthrough,
      active_minigame,
      active_check,
      active_rule_check,
      active_mode,
    } = get();
    if (!playthrough || !actionText.trim() || playthrough.is_spectator) return;
    if (active_minigame || active_check || active_rule_check) return;
    if (!playthrough.participant_id) return;
    if (playthrough.ended_outcome_tag) return;

    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: clientActionId ?? generateClientActionId(),
        action_text: actionText,
        action_kind: "narrative",
        action_mode: active_mode,
        voice_output_requested: isVoiceOutputRequested(),
      },
      actionText,
    );
  },

  submitMinigameResult: (result: MinigameResultPayload) => {
    const { playthrough, active_minigame, pending_minigame_result } = get();
    if (!playthrough || playthrough.is_spectator) return;
    if (!playthrough.participant_id) return;
    if (!active_minigame || active_minigame.minigame_id !== result.minigame_id)
      return;
    // Exactly once at the client boundary. The retry action below deliberately
    // resubmits this same immutable payload/attempt id.
    if (pending_minigame_result) return;

    const payload: MinigameResultPayload = {
      ...result,
      attempt_id: result.attempt_id ?? active_minigame.attempt_id,
    };
    const clientActionId = generateClientActionId();
    const actionText = minigameActionText(active_minigame, payload.outcome_tag);
    set({
      pending_minigame_result: {
        result: payload,
        action_text: actionText,
        client_action_id: clientActionId,
        attempts: 1,
        status: "submitting",
        fallback_used: false,
      },
    });
    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: clientActionId,
        action_text: actionText,
        action_kind: "minigame_result",
        action_mode: "do",
        minigame_result: payload,
        voice_output_requested: isVoiceOutputRequested(),
      },
      actionText,
    );
  },

  retryMinigameResult: async () => {
    const { playthrough, pending_minigame_result } = get();
    if (
      !playthrough ||
      !playthrough.participant_id ||
      !pending_minigame_result ||
      pending_minigame_result.status !== "retryable" ||
      pending_minigame_result.attempts >= MAX_MINIGAME_RESULT_ATTEMPTS
    )
      return;
    // A dropped SSE can mean the server committed successfully. Never replay
    // an outcome until a fresh authoritative read proves this attempt is still
    // pending; this also makes the timeout fallback safe after a lost "done".
    set({
      pending_minigame_result: {
        ...pending_minigame_result,
        status: "reconciling",
      },
    });
    try {
      const serverPlaythrough = await getPlaythrough(
        playthrough.playthrough_id,
      );
      const serverPending = pendingMinigameFromServer(serverPlaythrough.state);
      void queryClient.setQueryData(
        ["playthrough", playthrough.playthrough_id],
        serverPlaythrough,
      );
      if (
        !isSamePendingAttempt(serverPending, pending_minigame_result.result)
      ) {
        set({
          active_minigame: serverPending,
          pending_minigame_result: null,
          is_narrating: false,
        });
        return;
      }
    } catch (error) {
      // Reconciliation itself failed. Keep the outcome rather than gambling
      // on a duplicate POST; the player can safely retry this check.
      logEvent("warning", "minigame_result_reconciliation_failed", {
        playthrough_id: playthrough.playthrough_id,
        message: error instanceof Error ? error.message : String(error),
      });
      set((s) => ({
        pending_minigame_result:
          s.pending_minigame_result &&
          s.pending_minigame_result.result === pending_minigame_result.result
            ? { ...s.pending_minigame_result, status: "retryable" }
            : s.pending_minigame_result,
      }));
      return;
    }

    const attempts = pending_minigame_result.attempts + 1;
    set((s) => ({
      pending_minigame_result:
        s.pending_minigame_result &&
        s.pending_minigame_result.result === pending_minigame_result.result
          ? { ...s.pending_minigame_result, attempts, status: "submitting" }
          : s.pending_minigame_result,
    }));
    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: pending_minigame_result.client_action_id,
        action_text: pending_minigame_result.action_text,
        action_kind: "minigame_result",
        action_mode: "do",
        minigame_result: pending_minigame_result.result,
        voice_output_requested: isVoiceOutputRequested(),
      },
      pending_minigame_result.action_text,
    );
  },

  submitMinigameTimeoutFallback: async () => {
    const { playthrough, pending_minigame_result } = get();
    if (
      !playthrough ||
      !playthrough.participant_id ||
      !pending_minigame_result ||
      pending_minigame_result.status !== "terminal" ||
      pending_minigame_result.fallback_used
    )
      return;
    set({
      pending_minigame_result: {
        ...pending_minigame_result,
        status: "reconciling",
      },
    });
    try {
      const serverPlaythrough = await getPlaythrough(
        playthrough.playthrough_id,
      );
      const serverPending = pendingMinigameFromServer(serverPlaythrough.state);
      void queryClient.setQueryData(
        ["playthrough", playthrough.playthrough_id],
        serverPlaythrough,
      );
      if (
        !isSamePendingAttempt(serverPending, pending_minigame_result.result)
      ) {
        set({
          active_minigame: serverPending,
          pending_minigame_result: null,
          is_narrating: false,
        });
        return;
      }
    } catch (error) {
      logEvent("warning", "minigame_timeout_fallback_reconciliation_failed", {
        playthrough_id: playthrough.playthrough_id,
        message: error instanceof Error ? error.message : String(error),
      });
      set((s) => ({
        pending_minigame_result:
          s.pending_minigame_result &&
          s.pending_minigame_result.result === pending_minigame_result.result
            ? { ...s.pending_minigame_result, status: "terminal" }
            : s.pending_minigame_result,
      }));
      return;
    }
    const result = {
      ...pending_minigame_result.result,
      outcome_tag: "timeout" as const,
      score: undefined,
    };
    const fallbackClientActionId = generateClientActionId();
    const fallbackActionText = minigameActionText(get().active_minigame, "timeout");
    set({
      pending_minigame_result: {
        ...pending_minigame_result,
        result,
        action_text: fallbackActionText,
        client_action_id: fallbackClientActionId,
        attempts: 1,
        status: "submitting",
        fallback_used: true,
      },
    });
    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: fallbackClientActionId,
        action_text: fallbackActionText,
        action_kind: "minigame_result",
        action_mode: "do",
        minigame_result: result,
        voice_output_requested: isVoiceOutputRequested(),
      },
      fallbackActionText,
    );
  },

  clearActiveMinigame: () =>
    set({ active_minigame: null, pending_minigame_result: null }),

  finishClientEffect: () =>
    set((s) => ({
      active_client_effect: s.queued_client_effects[0] ?? null,
      queued_client_effects: s.queued_client_effects.slice(1),
    })),

  submitCheckResolution: (resolution: CheckResolutionPayload) => {
    const { playthrough, active_check } = get();
    if (!playthrough || playthrough.is_spectator) return;
    if (!playthrough.participant_id) return;
    if (!active_check || active_check.check_id !== resolution.check_id) return;

    // Only "attempt" needs the roll-reveal animation — "decline" has no
    // roll to hide and streams like any other turn.
    const isAttempt = resolution.resolution === "attempt";
    set({
      is_check_animation_pending: isAttempt,
      resolved_check_outcome: null,
      buffered_check_narration: "",
      check_terminal_pending: null,
    });

    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: generateClientActionId(),
        action_text: CHECK_RESOLUTION_ACTION_TEXT,
        action_kind: "check_resolution",
        action_mode: "do",
        check_resolution: resolution,
        voice_output_requested: isVoiceOutputRequested(),
      },
      CHECK_RESOLUTION_ACTION_TEXT,
    );
  },

  submitCheckReport: (report: CheckReportPayload, actionLabel: string) => {
    const { playthrough, active_rule_check, is_rule_check_submitting } = get();
    if (!playthrough || playthrough.is_spectator) return;
    if (!playthrough.participant_id) return;
    if (!active_rule_check || active_rule_check.check_id !== report.check_id) {
      return;
    }
    if (is_rule_check_submitting) return;

    set({
      is_rule_check_submitting: true,
      last_check_report: { report, label: actionLabel },
    });
    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: generateClientActionId(),
        action_text: actionLabel,
        action_kind: "check_report",
        action_mode: "do",
        check_report: report,
        voice_output_requested: isVoiceOutputRequested(),
      },
      actionLabel,
    );
  },

  armRuleCheck: async (checkId: string) => {
    const { playthrough, active_rule_check } = get();
    if (!playthrough?.participant_id || playthrough.is_spectator) return;
    if (!active_rule_check || active_rule_check.check_id !== checkId) return;
    if (isRuleCheckArmed(active_rule_check)) return;

    const armed = await armRuleCheck({
      playthrough_id: playthrough.playthrough_id,
      participant_id: playthrough.participant_id,
      check_id: checkId,
    });
    const current = get().active_rule_check;
    if (!current || current.check_id !== checkId) return;
    set({
      active_rule_check: toActiveRuleCheck(
        { ...current, is_armed: true, issued_at: armed.issued_at },
        armed.server_time_ms,
        Date.now(),
      ),
    });
  },

  // Called by the overlay once its fixed-duration animation timer elapses.
  // Flushes buffered narration and replays whatever terminal event arrived
  // (or hasn't yet — the stream may still be in flight, in which case
  // subsequent narration/done/degraded events proceed normally from here).
  revealCheckAnimation: () => {
    if (!get().is_check_animation_pending) return;
    const { buffered_check_narration, check_terminal_pending } = get();
    set((s) => ({
      is_check_animation_pending: false,
      streaming_text: s.streaming_text + buffered_check_narration,
      buffered_check_narration: "",
      check_terminal_pending: null,
    }));
    if (check_terminal_pending?.kind === "done") {
      get()._commitStreamedTurn(
        check_terminal_pending.actionText,
        check_terminal_pending.turnId,
      );
    } else if (check_terminal_pending?.kind === "degraded") {
      get()._degradeCurrentTurn(check_terminal_pending.message);
    }
  },

  stopGeneration: () => {
    const { cancel_stream_fn } = get();
    if (cancel_stream_fn) {
      cancel_stream_fn();
    }
    set({
      is_narrating: false,
      streaming_text: "",
      cancel_stream_fn: null,
      pending_chapter_delta: null,
      pending_minigame_trigger: null,
      pending_playthrough_ended: null,
      stream_generation: get().stream_generation + 1,
      pending_scene_image_url: null,
      pending_audio_url: null,
      pending_check_trigger: null,
      pending_rule_check_trigger: null,
      is_rule_check_submitting: false,
      is_check_animation_pending: false,
      buffered_check_narration: "",
      check_terminal_pending: null,
      resolved_check_outcome: null,
    });
  },

  retryLastTurn: () => {
    const { last_check_report, last_client_action_id, playthrough } = get();
    const turnNumber = nextTurnNumber(playthrough);
    const playthroughId = playthrough?.playthrough_id;
    if (last_check_report) {
      emitTurnRetry(
        "check_report_resend",
        turnNumber,
        last_client_action_id ?? generateClientActionId(),
        playthroughId,
      );
      get()._resendCheckReport(last_check_report.report, last_check_report.label);
      return;
    }
    const { last_submitted_action, submitTurn } = get();
    if (last_submitted_action && last_client_action_id) {
      emitTurnRetry("after_error", turnNumber, last_client_action_id, playthroughId);
      submitTurn(last_submitted_action, last_client_action_id);
    }
  },

  // Internal helpers (not part of the public store surface — no consumer
  // outside this file should call these directly).
  //
  // Shared SSE-stream machinery for both a normal narrative action and a
  // minigame result submission — the only difference between the two is the
  // POST body and the actionText used for the local turn log entry, so both
  // public actions build a TurnStreamBody and delegate here rather than each
  // wiring up createPostSSEConnection/onEvent themselves.
  _startTurnStream: (body: TurnStreamBody, actionTextForLog: string) => {
    const { cancel_stream_fn } = get();
    if (cancel_stream_fn) cancel_stream_fn();

    const generation = get().stream_generation + 1;
    const telemetry = startTurnStreamTelemetry(
      nextTurnNumber(get().playthrough),
      get().playthrough?.playthrough_id,
      get().last_client_action_id === body.client_action_id,
    );
    set({
      is_narrating: true,
      streaming_text: "",
      last_submitted_action: actionTextForLog,
      last_client_action_id: body.client_action_id,
      is_turn_paused: false,
      degraded_message: null,
      quota_notice_message: null,
      input_truncated_message: null,
      is_action_drawer_open: false,
      stream_generation: generation,
      ...(get().effects_action_id === body.client_action_id
        ? {}
        : { pending_client_effects: [] }),
    });

    const token = useAuthStore.getState().accessToken;
    const requestId = generateRequestId();
    setCurrentRequestId(requestId);
    let reachedTerminalEvent = false;
    let sawMemoryDegraded = false;
    const ownsStream = () => get().stream_generation === generation;
    const failMinigameResult = (message: string) => {
      if (!ownsStream()) return;
      const pending = get().pending_minigame_result;
      if (body.action_kind !== "minigame_result" || !pending) {
        get()._degradeCurrentTurn(message);
        return;
      }
      const terminal =
        pending.fallback_used ||
        pending.attempts >= MAX_MINIGAME_RESULT_ATTEMPTS;
      set({
        is_narrating: false,
        streaming_text: "",
        cancel_stream_fn: null,
        pending_chapter_delta: null,
        pending_minigame_trigger: null,
        pending_playthrough_ended: null,
        pending_audio_url: null,
        degraded_message: null,
        pending_minigame_result: {
          ...pending,
          status: terminal ? "terminal" : "retryable",
        },
      });
    };
    const handlers: SSEHandlers = {
      onEvent: (eventName: string, data: string) => {
        if (!ownsStream()) return;
        if (eventName === "mood") {
          const mood = data as ScenarioMood;
          const trackUrl = getMoodTrackUrl(
            mood,
            get().playthrough?.music_tracks,
          );
          if (!shouldIgnoreNarratorMood(get().playthrough)) {
            ambientSoundtrack.transitionTo(mood, trackUrl);
          }
        } else if (eventName === "narration") {
          telemetry.markFirstToken();
          if (get().is_check_animation_pending) {
            set((s) => ({
              buffered_check_narration: s.buffered_check_narration + data,
            }));
          } else {
            set((s) => ({ streaming_text: s.streaming_text + data }));
          }
        } else if (eventName === "check_resolved") {
          const payload = JSON.parse(data) as
            | CheckResolvedPayload
            | RuleCheckResolvedPayload;
          if ("kind" in payload && isRuleCheckKind(payload.kind)) {
            set({
              active_rule_check: null,
              is_rule_check_submitting: false,
              last_closed_rule_check_id: payload.check_id,
            });
          } else {
            set({ resolved_check_outcome: payload as CheckResolvedPayload });
          }
        } else if (eventName === "check") {
          // Buffered like pending_minigame_trigger — does NOT set
          // reachedTerminalEvent, since "done" still follows normally.
          const payload: unknown = JSON.parse(data);
          if (isRuleCheckPayload(payload)) {
            set({
              pending_rule_check_trigger: toActiveRuleCheck(
                payload,
                payload.server_time_ms ?? null,
                Date.now(),
              ),
            });
          } else {
            set({
              pending_check_trigger: {
                ...(payload as CheckEventPayload),
                resolved_roll: null,
              },
            });
          }
        } else if (eventName === "state_update") {
          // Applied at once, before narration, so the HUD matches the state the
          // narrator writes against; the post-commit refetch reconciles the rest.
          const payload = JSON.parse(data) as {
            state?: Record<string, unknown>;
            rule_sheet?: RuleSheetItem[];
          };
          const visibleState = payload.state;
          if (visibleState) {
            const previousSheet = get().playthrough?.rule_sheet ?? [];
            set((s) => ({
              playthrough: s.playthrough && {
                ...s.playthrough,
                state: visibleState,
                rule_sheet: payload.rule_sheet ?? s.playthrough.rule_sheet,
              },
            }));
            if (hasNewlyRevealedRule(previousSheet, payload.rule_sheet)) {
              handleRuleRevealed(get().playthrough?.enabled_tools ?? []);
            }
          }
        } else if (eventName === "sensory_cue") {
          // Performed immediately (cut, dead air, sound) and never buffered;
          // not a terminal event, narration follows.
          const cue = JSON.parse(data) as Parameters<typeof handleSensoryCue>[0];
          const { cue_played_action_id, cue_played_generation } = get();
          const isRetryOfPlayedAction =
            cue_played_action_id === body.client_action_id &&
            cue_played_generation !== generation;
          if (isRetryOfPlayedAction || !isSensoryCueId(cue.cue)) return;
          set({
            cue_played_action_id: body.client_action_id,
            cue_played_generation: generation,
          });
          handleSensoryCue(cue);
        } else if (eventName === "client_effect") {
          const effect = parseClientEffect(data);
          const { effects_action_id, effects_generation } = get();
          const isRetryOfQueuedAction =
            effects_action_id === body.client_action_id &&
            effects_generation !== generation;
          if (!effect || isRetryOfQueuedAction) return;
          set((s) => ({
            effects_action_id: body.client_action_id,
            effects_generation: generation,
            pending_client_effects: [...s.pending_client_effects, effect],
          }));
        } else if (eventName === "turn_summary") {
          const payload = JSON.parse(data) as TurnSummaryEventPayload;
          set((s) => ({
            pending_chapter_delta: mapTurnSummaryEvent(payload),
            playthrough: s.playthrough && {
              ...s.playthrough,
              active_conditions: payload.active_conditions,
            },
          }));
        } else if (eventName === "minigame") {
          // Buffered like pending_chapter_delta — does NOT set
          // reachedTerminalEvent, since "done" still follows normally.
          const payload = JSON.parse(data) as MinigameEventPayload;
          set({ pending_minigame_trigger: payload });
        } else if (eventName === "playthrough_ended") {
          // Buffered like pending_chapter_delta — does NOT set
          // reachedTerminalEvent, since "done" still follows normally.
          const payload = JSON.parse(data) as PlaythroughEndedPayload;
          set({ pending_playthrough_ended: payload });
        } else if (eventName === "scene_image") {
          // Buffered like pending_chapter_delta — does NOT set
          // reachedTerminalEvent, since "done" still follows normally.
          set({ pending_scene_image_url: data });
        } else if (eventName === "narration_audio") {
          // Buffered like pending_scene_image_url — does NOT set
          // reachedTerminalEvent, since "done" still follows normally.
          set({ pending_audio_url: data });
        } else if (eventName === "quota_notice") {
          const payload = JSON.parse(data) as QuotaNoticePayload;
          set({ quota_notice_message: payload.detail });
        } else if (eventName === "input_truncated") {
          const payload = JSON.parse(data) as InputTruncatedPayload;
          set({
            input_truncated_message: `Your action was too long, so only the first ${payload.max_length} characters were used.`,
          });
        } else if (eventName === "memory_degraded") {
          const payload = JSON.parse(data) as MemoryDegradedPayload;
          sawMemoryDegraded = true;
          set({ memory_degraded_reasons: payload.reasons });
        } else if (eventName === "done") {
          reachedTerminalEvent = true;
          telemetry.recordDone();
          if (!sawMemoryDegraded) set({ memory_degraded_reasons: [] });
          get()._commitStreamedTurn(actionTextForLog, parseDoneTurnId(data));
        } else if (eventName === "degraded") {
          reachedTerminalEvent = true;
          failMinigameResult(data);
        }
      },
      onError: (error: unknown) => {
        reachedTerminalEvent = true;
        telemetry.recordStall();
        if (isAlphaPausedError(error)) set({ is_turn_paused: true });
        failMinigameResult(
          isRateLimitError(error) || isAlphaPausedError(error)
            ? error.message
            : "Connection lost. Your turn may not have saved — you can try again.",
        );
      },
      onClose: () => {
        // The connection ended without "done"/"degraded"/onError firing —
        // e.g. the server's stream broke mid-generation after headers were
        // already sent. Without this, the UI would hang on "thinking"
        // forever with no way for the player to recover.
        if (!reachedTerminalEvent) {
          telemetry.recordStall();
          failMinigameResult(
            "The narrator stopped responding unexpectedly. Please try again.",
          );
        }
      },
    };

    const cancelFn = createPostSSEConnection(
      `${TRS_BASE_URL}/v1/turn`,
      body,
      token,
      handlers,
      requestId,
    );

    if (ownsStream()) set({ cancel_stream_fn: cancelFn });
  },

  _resendCheckReport: (report: CheckReportPayload, label: string) => {
    const { playthrough } = get();
    if (!playthrough?.participant_id || playthrough.is_spectator) return;
    set({ is_rule_check_submitting: true });
    get()._startTurnStream(
      {
        playthrough_id: playthrough.playthrough_id,
        participant_id: playthrough.participant_id,
        client_action_id: generateClientActionId(),
        action_text: label,
        action_kind: "check_report",
        action_mode: "do",
        check_report: report,
        voice_output_requested: isVoiceOutputRequested(),
      },
      label,
    );
  },

  _commitStreamedTurn: (actionText: string, turnId?: string) => {
    if (get().is_check_animation_pending) {
      set({
        check_terminal_pending: { kind: "done", actionText, message: "", turnId },
      });
      return;
    }
    const {
      playthrough,
      streaming_text,
      active_mode,
      pending_chapter_delta,
      pending_minigame_trigger,
      pending_check_trigger,
      pending_rule_check_trigger,
      pending_playthrough_ended,
      pending_scene_image_url,
      pending_audio_url,
    } = get();
    if (!playthrough) return;

    const newTurn: TurnLogItem = {
      id: turnId ?? `local-${Date.now()}`,
      turn_number: playthrough.turns.length + 1,
      action_mode: active_mode,
      action_text: actionText,
      narration_text: streaming_text,
      created_at: new Date().toISOString(),
      chapter_delta: pending_chapter_delta ?? undefined,
      image_url: pending_scene_image_url ?? undefined,
      audio_url: pending_audio_url ?? undefined,
    };

    set({
      playthrough: {
        ...playthrough,
        turns: [...playthrough.turns, newTurn],
        // Promote the buffered ending onto the committed playthrough — mirrors
        // pending_chapter_delta being attached to newTurn above. Falls back to
        // whatever was already there (null for an in-progress playthrough) when
        // nothing ended this turn.
        ended_outcome_tag:
          pending_playthrough_ended?.outcome_tag ??
          playthrough.ended_outcome_tag,
        ended_outcome_title:
          pending_playthrough_ended?.outcome_title ??
          playthrough.ended_outcome_title,
        ended_outcome_text:
          pending_playthrough_ended?.outcome_text ??
          playthrough.ended_outcome_text,
      },
      is_narrating: false,
      streaming_text: "",
      cancel_stream_fn: null,
      // The turn saved, so a later retry is a new action, not a replay.
      last_client_action_id: null,
      cue_played_action_id: null,
      ...queueCommittedEffects(get()),
      pending_chapter_delta: null,
      pending_minigame_trigger: null,
      pending_playthrough_ended: null,
      pending_minigame_result: null,
      pending_scene_image_url: null,
      pending_audio_url: null,
      pending_check_trigger: null,
      pending_rule_check_trigger: null,
      is_rule_check_submitting: false,
      last_check_report: null,
      resolved_check_outcome: null,
      // Promote the buffered trigger into the overlay-driving field now that
      // the triggering turn is fully committed — mirrors pending_chapter_delta
      // being attached to newTurn above. When nothing triggered this turn,
      // this resolves to null, which is always correct here: a normal turn
      // never has an active_minigame set (submission is gated on none being
      // pending), and a minigame-result turn's overlay was already cleared
      // via clearActiveMinigame() before this stream started.
      active_minigame: pending_minigame_trigger ?? null,
      // Same reasoning as active_minigame above, for a proposed check.
      active_check: pending_check_trigger ?? null,
      // And for a rule check; a prompt that just opened has its whole window.
      active_rule_check: pending_rule_check_trigger,
    });

    void queryClient.invalidateQueries({
      queryKey: ["playthrough-turns", playthrough.playthrough_id],
    });
    void queryClient.invalidateQueries({
      queryKey: ["playthrough", playthrough.playthrough_id],
    });
  },

  _degradeCurrentTurn: (message: string) => {
    if (get().is_check_animation_pending) {
      set({
        check_terminal_pending: { kind: "degraded", actionText: "", message },
      });
      return;
    }
    set({
      is_narrating: false,
      streaming_text: "",
      cancel_stream_fn: null,
      pending_chapter_delta: null,
      pending_minigame_trigger: null,
      pending_playthrough_ended: null,
      pending_scene_image_url: null,
      pending_audio_url: null,
      pending_check_trigger: null,
      pending_rule_check_trigger: null,
      is_rule_check_submitting: false,
      degraded_message: message,
    });
  },
}));

// Keep store active_mood always in sync with ambientSoundtrack
ambientSoundtrack.onMoodChange((mood) => {
  usePlayStore.setState({ active_mood: mood });
});

// Keep store playing_audio_turn_id always in sync with narrationPlayback
narrationPlayback.onPlaybackChange((turnId) => {
  usePlayStore.setState({ playing_audio_turn_id: turnId });
});

// Keep reader preferences in sync when they change outside the play feature
// (the onboarding wizard writes them through the shared store).
useReaderPreferencesStore.subscribe((prefs) => {
  usePlayStore.setState({
    reader_font_override: prefs.fontId,
    ebook_theme: prefs.theme,
    reader_font_size: prefs.fontSize,
  });
});
