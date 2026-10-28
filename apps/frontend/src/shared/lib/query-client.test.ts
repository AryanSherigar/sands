import { describe, expect, it } from "vitest";
import { shouldRetryQuery } from "./query-client";
import { RateLimitError } from "./rate-limit-error";

describe("shouldRetryQuery", () => {
  it("retries an ordinary failure once", () => {
    expect(shouldRetryQuery(0, new Error("network"))).toBe(true);
    expect(shouldRetryQuery(1, new Error("network"))).toBe(false);
  });

  it("never retries a rate-limited request", () => {
    const error = new RateLimitError(
      {
        detail: "Too many requests.",
        code: "rate_limited",
        scope: "read",
        reset_at: null,
      },
      30,
    );

    expect(shouldRetryQuery(0, error)).toBe(false);
  });
});
