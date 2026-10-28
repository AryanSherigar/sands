import { describe, expect, it } from "vitest";
import { toMessageCode, toRouteLabel } from "./alpha-client-error";

describe("alpha-client-error", () => {
  it("keeps only a short code, never the message", () => {
    expect(toMessageCode({ code: "ERR_NETWORK", message: "a@b.com broke" })).toBe(
      "ERR_NETWORK",
    );
    expect(toMessageCode(new TypeError("secret text"))).toBe("TypeError");
    expect(toMessageCode("a string with spaces")).toBe("unknown");
    expect(toMessageCode(null)).toBe("unknown");
  });

  it("rejects a code that is not in the safe alphabet", () => {
    expect(toMessageCode({ code: "has spaces and @" })).toBe("unknown");
  });

  it("replaces ids in the route", () => {
    expect(
      toRouteLabel("/play/3f2b8a4e-1c9d-4e7a-9b6f-0a1b2c3d4e5f/turns"),
    ).toBe("/play/:id/turns");
  });
});
