import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const indexCss = readFileSync(resolve(process.cwd(), "src/index.css"), "utf-8");
const themeBlock = indexCss.slice(indexCss.indexOf("@theme"));

function getThemeValue(name: string): string | undefined {
  const match = themeBlock.match(new RegExp(`--${name}:\\s*([^;]+);`));
  return match?.[1].replace(/\s+/g, " ").trim();
}

describe("Quiet Cinematic Design Tokens", () => {
  it("defines required semantic colors in the Tailwind theme", () => {
    expect(getThemeValue("color-primary")).toBeDefined();
    expect(getThemeValue("color-primary-contrast")).toBeDefined();
    expect(getThemeValue("color-info")).toBeDefined();
  });

  it("defines standard corner radii adhering to Quiet Cinematic rules", () => {
    expect(getThemeValue("radius-sm")).toBe("0.375rem");
    expect(getThemeValue("radius-md")).toBe("0.625rem");
    expect(getThemeValue("radius")).toBe("0.625rem");
    expect(getThemeValue("radius-lg")).toBe("0.875rem");
  });

  it("defines standard floating and modal shadows", () => {
    expect(getThemeValue("shadow-float")).toBe("0 8px 24px -8px rgba(0, 0, 0, 0.5)");
    expect(getThemeValue("shadow-modal")).toBe("0 24px 64px -16px rgba(0, 0, 0, 0.6)");
  });
});
