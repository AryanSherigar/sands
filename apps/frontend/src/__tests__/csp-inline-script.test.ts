import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../..");
const INLINE_SCRIPT_PATTERN = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;

const readFrontendFile = (relativePath: string): string =>
  readFileSync(resolve(FRONTEND_ROOT, relativePath), "utf8");

const inlineScriptHashes = (html: string): string[] =>
  [...html.matchAll(INLINE_SCRIPT_PATTERN)].map(
    (match) => `'sha256-${createHash("sha256").update(match[1]).digest("base64")}'`,
  );

describe("Content-Security-Policy and the inline theme script", () => {
  it("allows every inline script in index.html by its hash", () => {
    const hashes = inlineScriptHashes(readFrontendFile("index.html"));
    const scriptSource = readFrontendFile("public/_headers").match(/script-src[^;]*/)?.[0] ?? "";

    expect(hashes.length).toBeGreaterThan(0);
    for (const hash of hashes) {
      expect(scriptSource).toContain(hash);
    }
  });

  it("does not open script-src to arbitrary inline code", () => {
    const scriptSource = readFrontendFile("public/_headers").match(/script-src[^;]*/)?.[0] ?? "";

    expect(scriptSource).not.toContain("'unsafe-inline'");
  });
});
