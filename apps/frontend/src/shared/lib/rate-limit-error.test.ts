import { describe, expect, it } from "vitest";
import {
  RateLimitError,
  isRateLimitError,
  parseRateLimitError,
} from "./rate-limit-error";

const QUOTA_BODY = {
  detail: "You've reached today's turn limit. It resets at 00:00 UTC.",
  code: "quota_exceeded",
  scope: "turn",
  reset_at: "2026-10-27T00:00:00Z",
};

describe("parseRateLimitError", () => {
  it("builds a typed error from a 429 body and Retry-After header", () => {
    const error = parseRateLimitError(429, QUOTA_BODY, "3600");

    expect(error).toBeInstanceOf(RateLimitError);
    expect(error?.message).toBe(QUOTA_BODY.detail);
    expect(error?.code).toBe("quota_exceeded");
    expect(error?.scope).toBe("turn");
    expect(error?.resetAt?.toISOString()).toBe("2026-10-27T00:00:00.000Z");
    expect(error?.retryAfterSeconds).toBe(3600);
  });

  it("accepts a quota-store 503 without reset time or Retry-After", () => {
    const body = {
      detail: "This feature is temporarily unavailable.",
      code: "quota_unavailable",
      scope: "turn",
      reset_at: null,
    };

    const error = parseRateLimitError(503, body, null);

    expect(error?.resetAt).toBeNull();
    expect(error?.retryAfterSeconds).toBeNull();
  });

  it("ignores other statuses and non-rate-limit bodies", () => {
    expect(parseRateLimitError(400, QUOTA_BODY, null)).toBeNull();
    expect(parseRateLimitError(429, { detail: "Too many" }, null)).toBeNull();
    expect(parseRateLimitError(503, { detail: "down" }, null)).toBeNull();
  });

  it("narrows unknown errors", () => {
    expect(isRateLimitError(parseRateLimitError(429, QUOTA_BODY, null))).toBe(
      true,
    );
    expect(isRateLimitError(new Error("boom"))).toBe(false);
  });
});
