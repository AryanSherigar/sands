import { describe, expect, it } from "vitest";
import { fitToTraceSide } from "./traceSize";

describe("fitToTraceSide", () => {
  it("leaves small pictures alone", () => {
    expect(fitToTraceSide({ width: 1376, height: 768 })).toEqual({ width: 1376, height: 768 });
  });

  it("scales the long side down to the cap and keeps the aspect ratio", () => {
    expect(fitToTraceSide({ width: 4096, height: 2048 })).toEqual({ width: 2048, height: 1024 });
  });
});
