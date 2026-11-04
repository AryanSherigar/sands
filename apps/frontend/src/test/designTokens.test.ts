import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const indexCss = readFileSync(resolve(process.cwd(), "src/index.css"), "utf-8");
const themeBlock = indexCss.slice(indexCss.indexOf("@theme"));

function getThemeValue(name: string): string | undefined {
  const match = themeBlock.match(new RegExp(`--${name}:\\s*([^;]+);`));
  return match?.[1].replace(/\s+/g, " ").trim();
}

describe("Quiet Cinematic Design Tokens & Wilds Atmosphere", () => {
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

  it("defines Wilds Atmosphere light mode tokens at :root", () => {
    expect(indexCss).toContain("--surface-sunken: 239 228 200;");
    expect(indexCss).toContain("--surface: 243 234 211;");
    expect(indexCss).toContain("--surface-raised: 247 240 220;");
    expect(indexCss).toContain("--content: 58 49 40;");
    expect(indexCss).toContain("--primary: 70 96 110;");
  });

  it("defines dark mode tokens under .dark class", () => {
    const darkSection = indexCss.slice(indexCss.indexOf(".dark {"));
    expect(darkSection).toContain("--surface-sunken: 12 12 14;");
    expect(darkSection).toContain("--surface: 17 17 19;");
    expect(darkSection).toContain("--content: 237 237 239;");
    expect(darkSection).toContain("--primary: 237 237 239;");
  });
});
