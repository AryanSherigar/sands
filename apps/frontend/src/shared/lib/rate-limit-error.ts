import type {
  RateLimitCode,
  RateLimitErrorBody,
} from "../types/rateLimit.types";

const RATE_LIMIT_CODES: readonly RateLimitCode[] = [
  "rate_limited",
  "quota_exceeded",
  "feature_unavailable",
  "quota_unavailable",
];

export const HTTP_TOO_MANY_REQUESTS = 429;
export const HTTP_SERVICE_UNAVAILABLE = 503;

/** A request refused by a rate limit or daily quota. Never retried automatically:
 * retrying only spends more of the same budget. */
export class RateLimitError extends Error {
  readonly code: RateLimitCode;
  readonly scope: string;
  readonly resetAt: Date | null;
  readonly retryAfterSeconds: number | null;

  constructor(body: RateLimitErrorBody, retryAfterSeconds: number | null) {
    super(body.detail);
    this.name = "RateLimitError";
    this.code = body.code;
    this.scope = body.scope;
    this.resetAt = body.reset_at ? new Date(body.reset_at) : null;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export const isRateLimitError = (error: unknown): error is RateLimitError =>
  error instanceof RateLimitError;

const isRateLimitBody = (body: unknown): body is RateLimitErrorBody => {
  if (typeof body !== "object" || body === null) return false;
  const candidate = body as Partial<RateLimitErrorBody>;
  return (
    typeof candidate.detail === "string" &&
    typeof candidate.scope === "string" &&
    RATE_LIMIT_CODES.includes(candidate.code as RateLimitCode)
  );
};

const parseRetryAfter = (header: string | null | undefined): number | null => {
  if (!header) return null;
  const seconds = Number.parseInt(header, 10);
  return Number.isNaN(seconds) ? null : seconds;
};

/** Returns a RateLimitError when a response is a rate-limit/quota refusal, else null. */
export const parseRateLimitError = (
  status: number,
  body: unknown,
  retryAfterHeader: string | null | undefined,
): RateLimitError | null => {
  const isLimitStatus =
    status === HTTP_TOO_MANY_REQUESTS || status === HTTP_SERVICE_UNAVAILABLE;
  if (!isLimitStatus || !isRateLimitBody(body)) return null;
  return new RateLimitError(body, parseRetryAfter(retryAfterHeader));
};
