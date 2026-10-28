import { useQuery } from "@tanstack/react-query";
import { decodeUrlToPixels } from "@/shared/lib/map-tracing/decodeImage";
import type { PixelImage } from "@/shared/types/strategy-map.types";

export function usePicturePixels(
  pictureUrl: string,
  size: { width: number; height: number },
): { pixels: PixelImage | null } {
  const query = useQuery<PixelImage, Error>({
    queryKey: ["region-map-picture", pictureUrl, size.width, size.height],
    queryFn: () => decodeUrlToPixels(pictureUrl, size),
    enabled: Boolean(pictureUrl),
    staleTime: Infinity,
  });
  return { pixels: query.data ?? null };
}
