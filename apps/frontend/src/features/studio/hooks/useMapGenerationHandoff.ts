import { useCallback, useEffect, useState } from "react";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import type { GeneratedMap, MapGenerationJob } from "../types/mapGeneration.types";
import { isMapJobActive } from "./useMapGenerationJob";

const REGION_FILE_NAME = "generated-regions.png";
const REGION_FILE_TYPE = "image/png";
const HANDOFF_ERROR_FALLBACK = "Could not open the generated map. Try again.";

async function downloadRegionImage(url: string): Promise<File> {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Could not download the generated region image");
  const blob = await response.blob();
  return new File([blob], REGION_FILE_NAME, { type: REGION_FILE_TYPE });
}

async function buildGeneratedMap(job: MapGenerationJob): Promise<GeneratedMap> {
  if (!job.region_image_url || !job.width || !job.height) {
    throw new Error("The generated map is incomplete");
  }
  const regionImage = await downloadRegionImage(job.region_image_url);
  const pictureUrl = job.picture_url ?? job.region_image_url;
  return {
    picture: { url: pictureUrl, size: { width: job.width, height: job.height } },
    regionImage,
    hasArt: job.has_art,
  };
}

export const useMapGenerationHandoff = (
  job: MapGenerationJob | null | undefined,
  onGeneratedMap: (generated: GeneratedMap) => void,
) => {
  const [watchedJobId, setWatchedJobId] = useState<string | null>(null);
  const [usedJobId, setUsedJobId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const claim = useCallback(
    async (target: MapGenerationJob): Promise<void> => {
      setUsedJobId(target.job_id);
      setErrorMessage(null);
      try {
        onGeneratedMap(await buildGeneratedMap(target));
      } catch (error) {
        setErrorMessage(extractErrorMessage(error, HANDOFF_ERROR_FALLBACK));
      }
    },
    [onGeneratedMap],
  );

  useEffect(() => {
    if (!job) return;
    if (isMapJobActive(job)) setWatchedJobId(job.job_id);
    const isWatchedAndDone = job.status === "succeeded" && job.job_id === watchedJobId;
    if (isWatchedAndDone && job.job_id !== usedJobId) void claim(job);
  }, [job, watchedJobId, usedJobId, claim]);

  const isReady = job?.status === "succeeded" && job.job_id !== usedJobId && job.job_id !== watchedJobId;

  return {
    readyJob: isReady ? job : null,
    claim,
    dismiss: (target: MapGenerationJob): void => setUsedJobId(target.job_id),
    errorMessage,
  };
};
