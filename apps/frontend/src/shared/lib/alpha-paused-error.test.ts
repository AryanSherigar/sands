import { describe, expect, it } from "vitest";
import {
  ALPHA_PAUSED_MESSAGE,
  AlphaPausedError,
  isAlphaPausedError,
  parseAlphaPausedError,
} from "./alpha-paused-error";

describe("parseAlphaPausedError", () => {
  it("recognises the 503 pause refusal and uses its own calm message", () => {
    const error = parseAlphaPausedError(503, {
      detail: "something the server said",
      code: "alpha_paused",
    });

    expect(isAlphaPausedError(error)).toBe(true);
    expect(error?.message).toBe(ALPHA_PAUSED_MESSAGE);
  });

  it("ignores other 503 bodies and other statuses", () => {
    expect(parseAlphaPausedError(503, { code: "quota_unavailable" })).toBeNull();
    expect(parseAlphaPausedError(429, { code: "alpha_paused" })).toBeNull();
    expect(parseAlphaPausedError(503, null)).toBeNull();
  });

  it("is not mistaken for another error type", () => {
    expect(isAlphaPausedError(new Error("x"))).toBe(false);
    expect(isAlphaPausedError(new AlphaPausedError())).toBe(true);
  });
});
