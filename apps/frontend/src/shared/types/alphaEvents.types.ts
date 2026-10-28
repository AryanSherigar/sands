export type AlphaEventPropsMap = {
  session_start: SessionStats;
  session_end: SessionStats;
  device_info: DeviceInfoProps;
  turn_perceived_latency: TurnPerceivedLatencyProps;
  stream_stall: StreamProblemProps;
  stream_reconnect: StreamProblemProps;
  audio_blocked: AudioBlockedProps;
  ui_used: UiUsedProps;
  client_error: ClientErrorProps;
  turn_retry: TurnRetryProps;
  tension_rating: TensionRatingProps;
};

export type AlphaEventName = keyof AlphaEventPropsMap;

interface SessionStats {
  visible_ms: number;
  hidden_ms: number;
  turns_in_session?: number;
  sfx_played_count: number;
  audio_blocked_count: number;
}

export interface DeviceInfoProps {
  device_class: "phone" | "tablet" | "desktop";
  viewport_bucket: string;
  browser_family: string;
  is_reduce_effects_on: boolean;
  is_audio_muted: boolean;
}

interface TurnPerceivedLatencyProps {
  turn_number: number;
  first_token_ms: number | null;
  total_ms: number;
}

interface StreamProblemProps {
  turn_number: number;
  stalled_ms: number;
}

export interface AudioBlockedProps {
  reason: "autoplay_policy" | "muted" | "error";
}

export type AlphaUiFeature = "rule_sheet" | "hud" | "map" | "phone";

interface UiUsedProps {
  feature: AlphaUiFeature;
  count: number;
}

interface ClientErrorProps {
  kind: string;
  route: string;
  message_code: string;
}

export type TurnRetryKind = "after_error" | "check_report_resend";

interface TurnRetryProps {
  kind: TurnRetryKind;
  turn_number: number;
  client_action_id: string;
}

interface TensionRatingProps {
  turn_number: number;
  rating: number;
}

export interface EmitOptions {
  playthroughId?: string;
}

export interface QueuedAlphaEvent {
  name: AlphaEventName;
  client_ts: string;
  playthrough_id?: string;
  props: Record<string, unknown>;
}
