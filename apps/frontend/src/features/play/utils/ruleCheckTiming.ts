import {
  ActiveRuleCheck,
  RuleCheckEventPayload,
} from "@/shared/types/check.types";

// `serverNowMs` is the server clock when the client learned of the check
// (PlaythroughResponse.server_time_ms on reload); null for a prompt that just
// arrived over SSE, which was issued a moment ago and so has its whole window.
export function toActiveRuleCheck(
  check: RuleCheckEventPayload,
  serverNowMs: number | null,
  clientNowMs: number,
): ActiveRuleCheck {
  const elapsedMs =
    serverNowMs === null ? 0 : Math.max(0, serverNowMs - check.issued_at);
  return {
    ...check,
    initial_remaining_ms: Math.max(0, check.window_ms - elapsedMs),
    started_at_client_ms: clientNowMs,
  };
}
