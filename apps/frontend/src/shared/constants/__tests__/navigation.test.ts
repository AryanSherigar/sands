import { describe, expect, it } from "vitest";
import { getPrimaryNavLinks, STUDIO_PATH } from "../navigation";

describe("getPrimaryNavLinks", () => {
  it("lists Discover and Studio in order", () => {
    const paths = getPrimaryNavLinks().map((link) => link.to);
    expect(paths).toContain(STUDIO_PATH);
    expect(paths.slice(0, 2)).toEqual(["/", "/discover"]);
  });
});
