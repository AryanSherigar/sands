import { describe, expect, it } from "vitest";
import {
  buildDiscoverHref,
  buildWelcomeHref,
  sanitizeRedirectTarget,
} from "./onboarding-routes";

describe("sanitizeRedirectTarget", () => {
  it("accepts internal paths", () => {
    expect(sanitizeRedirectTarget("/play/abc?x=1")).toBe("/play/abc?x=1");
  });

  it.each([null, "", "https://evil.example", "//evil.example", "/welcome"])(
    "rejects %s",
    (rawTarget) => {
      expect(sanitizeRedirectTarget(rawTarget)).toBeNull();
    },
  );
});

describe("buildWelcomeHref", () => {
  it("omits the redirect for the home page", () => {
    expect(buildWelcomeHref("/")).toBe("/welcome");
  });

  it("encodes the original destination", () => {
    expect(buildWelcomeHref("/studio?tab=1")).toBe(
      "/welcome?redirect=%2Fstudio%3Ftab%3D1",
    );
  });
});

describe("buildDiscoverHref", () => {
  it("returns plain discover without genres", () => {
    expect(buildDiscoverHref([])).toBe("/discover");
  });

  it("repeats the genre param for each pick", () => {
    expect(buildDiscoverHref(["Horror", "Sci-Fi"])).toBe(
      "/discover?genre=Horror&genre=Sci-Fi",
    );
  });
});
