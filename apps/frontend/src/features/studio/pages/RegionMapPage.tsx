import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { RegionMapEditor } from "../components/RegionMapEditor/RegionMapEditor";
import type { RegionMapResult } from "../components/RegionMapEditor/RegionMapEditor.types";
import {
  ALLOWED_COVER_IMAGE_TYPES,
  MAX_COVER_IMAGE_BYTES,
} from "../constants/upload";
import { useSaveRegionMap } from "../hooks/useSaveRegionMap";
import { useUploadMapImage } from "../hooks/useUploadMapImage";

interface Picture {
  url: string;
  size: { width: number; height: number };
}

const PICTURE_ERROR = "Use a JPEG, PNG or WebP picture under 5 MB.";

async function measure(file: File): Promise<{ width: number; height: number }> {
  const bitmap = await createImageBitmap(file);
  return { width: bitmap.width, height: bitmap.height };
}

export const RegionMapPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const upload = useUploadMapImage();
  const save = useSaveRegionMap(id ?? "");
  const [picture, setPicture] = useState<Picture | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);

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
      {!picture && (
        <label className="block space-y-2 text-sm">
          Map picture
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePictureChange} />
        </label>
      )}
      {message && <p role="alert" className="text-sm text-danger">{message}</p>}
      {picture && (
        <RegionMapEditor
          key={picture.url}
          pictureUrl={picture.url}
          pictureSize={picture.size}
          initialDocument={null}
          onFinish={handleFinish}
        />
      )}
      {save.errorMessage && <p role="alert" className="text-sm text-danger">{save.errorMessage}</p>}
      {isSaved && (
        <p role="status" className="text-sm text-success">
          Map saved.
        </p>
      )}
      {picture && !isSaved && (
        <Button variant="ghost" size="sm" onClick={() => setPicture(null)}>
          Choose a different picture
        </Button>
      )}
    </main>
  );
};
