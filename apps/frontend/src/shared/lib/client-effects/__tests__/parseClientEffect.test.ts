import { describe, expect, it, vi } from "vitest";
import { parseClientEffect } from "../parseClientEffect";

describe("parseClientEffect", () => {
  it("reads an input takeover", () => {
    const data = JSON.stringify({
      kind: "input_takeover",
      params: { text: "I feel too much", lock_ms: 5500, type_ms_per_char: 60 },
    });
    expect(parseClientEffect(data)).toEqual({
      kind: "input_takeover",
      params: { text: "I feel too much", lock_ms: 5500, type_ms_per_char: 60 },
    });
  });

  it("reads a phone echo", () => {
    const data = JSON.stringify({
      kind: "phone_echo",
      params: { record_ms: 6000, delay_ms: 2500 },
    });
    expect(parseClientEffect(data)?.kind).toBe("phone_echo");
  });

  it("rejects unknown kinds and bad params", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(parseClientEffect(JSON.stringify({ kind: "explode", params: {} }))).toBeNull();
    expect(
      parseClientEffect(
        JSON.stringify({ kind: "phone_echo", params: { record_ms: "x" } }),
      ),
    ).toBeNull();
    expect(parseClientEffect("not json")).toBeNull();
    warn.mockRestore();
  });
});
