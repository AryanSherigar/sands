const MAX_PORTRAIT_BYTES = 5 * 1024 * 1024;

const IMAGE_TYPE_BY_EXTENSION: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
};

const ACCEPTED_IMAGE_TYPES = new Set(Object.values(IMAGE_TYPE_BY_EXTENSION));

function getImageTypeFromUrl(url: string): string | undefined {
  const extension = new URL(url, window.location.href).pathname.split(".").pop()?.toLowerCase();
  return extension ? IMAGE_TYPE_BY_EXTENSION[extension] : undefined;
}

export async function fetchPortraitBlob(url: string): Promise<Blob> {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Portrait could not be loaded");
  const blob = await response.blob();
  if (ACCEPTED_IMAGE_TYPES.has(blob.type)) return blob;
  const inferredType = getImageTypeFromUrl(url);
  if (!inferredType) throw new Error("Portrait type is not supported");
  return new Blob([blob], { type: inferredType });
}

export function readPortraitAsDataUrl(image: Blob): Promise<string> {
  if (image.size > MAX_PORTRAIT_BYTES) return Promise.reject(new Error("Portrait exceeds 5 MB"));
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Could not read portrait"));
    reader.onerror = () => reject(new Error("Could not read portrait"));
    reader.readAsDataURL(image);
  });
}
