import React, { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import type { GeneratedMap } from "../types/mapGeneration.types";
import { RegionMapEditor } from "../components/RegionMapEditor/RegionMapEditor";
import type { RegionMapResult } from "../components/RegionMapEditor/RegionMapEditor.types";
import {
  ALLOWED_COVER_IMAGE_TYPES,
  MAX_COVER_IMAGE_BYTES,
} from "../constants/upload";
import { GenerateMapForm } from "../components/GenerateMapForm";
import { isMapJobActive, useMapGenerationJob } from "../hooks/useMapGenerationJob";
import { useMapGenerationHandoff } from "../hooks/useMapGenerationHandoff";
import { useSaveRegionMap } from "../hooks/useSaveRegionMap";
import { useStartMapGeneration } from "../hooks/useStartMapGeneration";
import { useStrategyMap } from "../hooks/useStrategyMap";
import { useUploadMapImage } from "../hooks/useUploadMapImage";

interface Picture {
  url: string;
  size: { width: number; height: number };
}

const PICTURE_ERROR = "Use a JPEG, PNG or WebP picture under 5 MB.";
const ART_FAILED_NOTICE = "The painted picture failed, showing the region colors. Choose a different picture to try again.";
const GENERATING_LABEL = "Generating your map in the background. You can leave this page and keep editing";
const START_ERROR_FALLBACK = "Failed to start map generation. Try again.";
const READY_NOTICE = "Your generated map is ready.";

async function measure(file: File): Promise<{ width: number; height: number }> {
  const bitmap = await createImageBitmap(file);
  return { width: bitmap.width, height: bitmap.height };
}

export const RegionMapPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const upload = useUploadMapImage();
  const save = useSaveRegionMap(id ?? "");
  const startGeneration = useStartMapGeneration(id ?? "");
  const { data: job } = useMapGenerationJob(id ?? "");
  const [description, setDescription] = useState("");
  const [startFile, setStartFile] = useState<File | null>(null);
  const [hasArt, setHasArt] = useState(true);
  const [picture, setPicture] = useState<Picture | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [isReplacing, setIsReplacing] = useState(false);
  const savedMap = useStrategyMap(id ?? "");
  const hasSavedMap = !isReplacing && Boolean(savedMap.data?.image_url);
  const activePicture: Picture | null =
    picture ??
    (hasSavedMap && savedMap.data?.image_url
      ? { url: savedMap.data.image_url, size: { width: savedMap.data.width, height: savedMap.data.height } }
      : null);
  const initialDocument = picture === null && hasSavedMap ? (savedMap.data ?? null) : null;
  const isGenerating = startGeneration.isPending || isMapJobActive(job);
  const generationError =
    (startGeneration.error && extractErrorMessage(startGeneration.error, START_ERROR_FALLBACK)) ||
    (job?.status === "failed" ? job.error_message : null);

  const handleGeneratedMap = useCallback((generated: GeneratedMap): void => {
    setStartFile(generated.regionImage);
    setHasArt(generated.hasArt);
    setPicture(generated.picture);
  }, []);
  const handoff = useMapGenerationHandoff(job, handleGeneratedMap);
  const readyJob = handoff.readyJob;

  const handlePictureChange = async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const isAllowed = ALLOWED_COVER_IMAGE_TYPES.includes(file.type) && file.size <= MAX_COVER_IMAGE_BYTES;
    if (!isAllowed) {
      setMessage(PICTURE_ERROR);
      return;
    }
    try {
      const [size, uploaded] = await Promise.all([measure(file), upload.mutateAsync(file)]);
      setMessage(null);
      setPicture({ url: uploaded.url, size });
    } catch (error) {
      setMessage(extractErrorMessage(error, "Failed to upload the map picture."));
    }
  };

  const handleGenerate = async (nextDescription: string): Promise<void> => {
    setDescription(nextDescription);
    setMessage(null);
    await startGeneration.mutateAsync(nextDescription).catch(() => null);
  };

  const handleChooseDifferentPicture = (): void => {
    setIsReplacing(true);
    setPicture(null);
    setStartFile(null);
    setHasArt(true);
  };

  const handleFinish = async (result: RegionMapResult): Promise<void> => {
    try {
      await save.mutateAsync(result.document);
      setIsSaved(true);
    } catch {
      setIsSaved(false);
    }
  };

  if (!id) return <p className="p-6 text-sm text-content-muted">No scenario ID provided.</p>;

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6 font-sans text-content">
      <h1 className="text-xl font-semibold">Map regions</h1>
      {!activePicture && (
        <GenerateMapForm
          initialDescription={description}
          isBusy={isGenerating}
          stageLabel={isGenerating ? GENERATING_LABEL : null}
          errorMessage={generationError ?? handoff.errorMessage}
          onGenerate={handleGenerate}
        />
      )}
      {!activePicture && isGenerating && (
        <Link className="block text-sm text-primary underline" to={`/studio/${id}/edit`}>
          Back to the scenario
        </Link>
      )}
      {!activePicture && readyJob && (
        <p role="status" className="space-x-3 text-sm text-success">
          <span>{READY_NOTICE}</span>
          <Button size="sm" onClick={() => handoff.claim(readyJob)}>
            Use this map
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handoff.dismiss(readyJob)}>
            Dismiss
          </Button>
        </p>
      )}
      {!activePicture && (
        <label className="block space-y-2 text-sm">
          Map picture
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePictureChange} />
        </label>
      )}
      {message && <p role="alert" className="text-sm text-danger">{message}</p>}
      {id && savedMap.isLoading && <p role="status" className="text-sm text-content-muted">Loading your map…</p>}
      {activePicture && (
        <RegionMapEditor
          key={activePicture.url}
          pictureUrl={activePicture.url}
          pictureSize={activePicture.size}
          initialDocument={initialDocument}
          startFile={startFile}
          onFinish={handleFinish}
        />
      )}
      {activePicture && !hasArt && <p role="status" className="text-sm text-content-muted">{ART_FAILED_NOTICE}</p>}
      {save.errorMessage && <p role="alert" className="text-sm text-danger">{save.errorMessage}</p>}
      {isSaved && (
        <p role="status" className="text-sm text-success">
          Map saved.
        </p>
      )}
      {activePicture && !isSaved && (
        <Button variant="ghost" size="sm" onClick={handleChooseDifferentPicture}>
          Choose a different picture
        </Button>
      )}
    </main>
  );
};
