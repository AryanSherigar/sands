import {
  MAX_REGION_IMAGE_BYTES,
  MAX_TRACE_SIDE,
  REGION_IMAGE_TYPE,
} from "@/shared/constants/mapTracing";
import { logEvent } from "@/shared/lib/logger";
import type {
  DecodedRegionImage,
  PixelImage,
  RegionImageRejection,
} from "@/shared/types/strategy-map.types";

export type RegionImageValidation =
  | { ok: true; image: PixelImage }
  | { ok: false; reason: RegionImageRejection };

export type DecodeRegionImage = (file: File) => Promise<DecodedRegionImage | null>;

/** Nearest-neighbour downscale (smoothing off) keeps flat colours flat. */
const decodeToPixels: DecodeRegionImage = async (file) => {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_TRACE_SIDE / Math.max(bitmap.width, bitmap.height));
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return null;
    context.imageSmoothingEnabled = false;
    context.drawImage(bitmap, 0, 0, width, height);
    const { data } = context.getImageData(0, 0, width, height);
    return {
      image: { width, height, data },
      originalSize: { width: bitmap.width, height: bitmap.height },
    };
  } catch (error) {
    logEvent("warning", "region_image_decode_failed", {
      message: error instanceof Error ? error.message : "unknown",
    });
    return null;
  }
};

export async function validateRegionImageFile(
  file: File,
  pictureSize: { width: number; height: number },
  decode: DecodeRegionImage = decodeToPixels,
): Promise<RegionImageValidation> {
  if (file.type !== REGION_IMAGE_TYPE) return { ok: false, reason: "not_png" };
  if (file.size > MAX_REGION_IMAGE_BYTES) return { ok: false, reason: "too_large" };
  const decoded = await decode(file);
  if (!decoded) return { ok: false, reason: "decode_failed" };
  const isSameSize =
    decoded.originalSize.width === pictureSize.width &&
    decoded.originalSize.height === pictureSize.height;
  if (!isSameSize) return { ok: false, reason: "size_mismatch" };
  return { ok: true, image: decoded.image };
}

export async function decodeUrlToPixels(
  url: string,
  size: { width: number; height: number },
): Promise<PixelImage> {
  const response = await fetch(url);
  const bitmap = await createImageBitmap(await response.blob());
  const canvas = document.createElement("canvas");
  canvas.width = size.width;
  canvas.height = size.height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas is not available");
  context.drawImage(bitmap, 0, 0, size.width, size.height);
  const { data } = context.getImageData(0, 0, size.width, size.height);
  return { width: size.width, height: size.height, data };
}
