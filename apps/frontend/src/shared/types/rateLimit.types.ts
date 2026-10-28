export type RateLimitCode =
  | "rate_limited"
  | "quota_exceeded"
  | "feature_unavailable"
  | "quota_unavailable";

/** Body of a 429 (or quota-store 503) from Core API or TRS. */
export interface RateLimitErrorBody {
  detail: string;
  code: RateLimitCode;
  scope: string;
  reset_at: string | null;
}

/** TRS `quota_notice` SSE event: an optional turn extra was skipped. */
export interface QuotaNoticePayload {
  feature: string;
  code: RateLimitCode;
  detail: string;
  reset_at: string | null;
}
