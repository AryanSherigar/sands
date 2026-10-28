import { describe, it, expect } from "vitest";
import { WILDS_COLORS } from "../wildsTheme.constants";

describe("Wilds Theme Constants", () => {
  it("defines the canonical Wilds Atmosphere palette values", () => {
    expect(WILDS_COLORS.parchmentBase).toBe("#F3EAD3");
    expect(WILDS_COLORS.parchmentPanel).toBe("#F7F0DC");
    expect(WILDS_COLORS.appBg).toBe("#EFE4C8");
    expect(WILDS_COLORS.primary).toBe("#2E4856");
    expect(WILDS_COLORS.tertiary).toBe("#7C2820");
    expect(WILDS_COLORS.meadowGreen).toBe("#5E8A5A");
  });
});
