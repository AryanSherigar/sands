import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { logEvent } from "@/shared/lib/logger";
import { generateMapArt, generateMapRegions } from "../api/mapGeneration.api";
import type { GenerateMapStage, GeneratedMap } from "../types/mapGeneration.types";

const REGION_FILE_NAME = "generated-regions.png";
const REGION_FILE_TYPE = "image/png";
const GENERATE_ERROR_FALLBACK = "Failed to generate the map. Try again.";

async function downloadRegionImage(url: string): Promise<File> {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Could not download the generated region image");
  const blob = await response.blob();
  return new File([blob], REGION_FILE_NAME, { type: REGION_FILE_TYPE });
}

export const useGenerateMap = (scenarioId: string) => {
  const [stage, setStage] = useState<GenerateMapStage>("idle");

  const mutation = useMutation<GeneratedMap, Error, string>({
    mutationFn: async (description) => {
      setStage("regions");
      const regions = await generateMapRegions(scenarioId, description);
      const regionImage = await downloadRegionImage(regions.region_image_url);
      const size = { width: regions.width, height: regions.height };
      setStage("art");
      try {
        const art = await generateMapArt(scenarioId, regionImage, description);
        return { picture: { url: art.picture_url, size }, regionImage, hasArt: true };
      } catch (error) {
        logEvent("warning", "map_art_generation_failed", {
          message: error instanceof Error ? error.message : "unknown",
        });
        return { picture: { url: regions.region_image_url, size }, regionImage, hasArt: false };
      }
    },
    onSettled: () => setStage("idle"),
  });

  return {
    generate: mutation.mutateAsync,
    stage,
    isGenerating: mutation.isPending,
    errorMessage: mutation.error ? extractErrorMessage(mutation.error, GENERATE_ERROR_FALLBACK) : null,
  };
};
