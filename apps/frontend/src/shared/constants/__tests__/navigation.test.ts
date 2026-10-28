import { describe, expect, it } from "vitest";
import { getPrimaryNavLinks, STUDIO_PATH } from "../navigation";

describe("getPrimaryNavLinks", () => {
  it("includes Studio when alpha mode is off", () => {
    const paths = getPrimaryNavLinks(false).map((link) => link.to);
    expect(paths).toContain(STUDIO_PATH);
  });

  it("drops Studio in alpha mode and keeps the rest in order", () => {
    const paths = getPrimaryNavLinks(true).map((link) => link.to);
    expect(paths).toEqual(["/", "/discover"]);
  });
});
