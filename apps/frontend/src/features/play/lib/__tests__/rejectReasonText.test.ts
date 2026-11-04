import { describe, expect, it } from "vitest";
import { describeRejectReason } from "../rejectReasonText";

describe("describeRejectReason", () => {
  it("turns a known rejection code into readable text", () => {
    expect(describeRejectReason("target_not_hostile")).toBe(
      "You can only attack a region held by a house you are at war with.",
    );
  });

  it("never shows a raw code it does not recognize", () => {
    expect(describeRejectReason("brand_new_code")).toBe("That order cannot be issued right now");
  });

  it("passes through a reason that is already readable text", () => {
    expect(describeRejectReason("Not enough mandates")).toBe("Not enough mandates");
  });

  it("falls back when there is no reason", () => {
    expect(describeRejectReason(null)).toBe("That order cannot be issued right now");
  });
});
