import { describe, it, expect } from "vitest";
import { DEFAULT_LETTER_SCENARIO } from "../../components/StrategyPlayScreen/letter/fixtures/defaultLetterScenario";
import type { StrategyLetterPackage } from "../letterScene.types";

describe("letterScene.types and DEFAULT_LETTER_SCENARIO", () => {
  it("conforms to the StrategyLetterPackage contract with Queen Mira dispatch", () => {
    const pkg: StrategyLetterPackage = DEFAULT_LETTER_SCENARIO;
    expect(pkg.dispatchNumber).toBe(8);
    expect(pkg.provenance.senderName).toBe("Queen Mira");
    expect(pkg.incoming.paragraphs.length).toBeGreaterThanOrEqual(3);
    expect(pkg.scribe.name).toBe("Brother Lucan");
    expect(pkg.initialDraft.paragraphs.length).toBeGreaterThan(0);
  });
});
