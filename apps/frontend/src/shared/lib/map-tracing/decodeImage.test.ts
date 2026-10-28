import { describe, expect, it } from "vitest";
import { validateRegionImageFile } from "./decodeImage";
import { makeBlockImage } from "./testImages";
import type { DecodedRegionImage } from "@/shared/types/strategy-map.types";

const SIZE = { width: 4, height: 2 };
const DECODED: DecodedRegionImage = {
  image: makeBlockImage(["ab"], { a: [255, 0, 0], b: [0, 0, 255] }, 2),
  originalSize: { width: 4, height: 2 },
};

function fileOf(type: string, bytes = 10): File {
  return new File([new Uint8Array(bytes)], "regions", { type });
}

const decodeOk = async (): Promise<DecodedRegionImage | null> => DECODED;

describe("validateRegionImageFile", () => {
  it("rejects anything that is not a PNG before decoding", async () => {
    const result = await validateRegionImageFile(fileOf("image/jpeg"), SIZE, decodeOk);
    expect(result).toEqual({ ok: false, reason: "not_png" });
  });

  it("rejects files over the size cap", async () => {
    const result = await validateRegionImageFile(fileOf("image/png", 6 * 1024 * 1024), SIZE, decodeOk);
    expect(result).toEqual({ ok: false, reason: "too_large" });
  });

  it("rejects an image whose size differs from the picture", async () => {
    const result = await validateRegionImageFile(fileOf("image/png"), { width: 5, height: 2 }, decodeOk);
    expect(result).toEqual({ ok: false, reason: "size_mismatch" });
  });

  it("reports a decode failure", async () => {
    const result = await validateRegionImageFile(fileOf("image/png"), SIZE, async () => null);
    expect(result).toEqual({ ok: false, reason: "decode_failed" });
  });

  it("returns the pixels for a matching PNG", async () => {
    const result = await validateRegionImageFile(fileOf("image/png"), SIZE, decodeOk);
    expect(result).toEqual({ ok: true, image: DECODED.image });
  });
});
