import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import type { StartChooserProps } from "./RegionMapEditor.types";

export const StartChooser: React.FC<StartChooserProps> = ({
  errorMessage,
  isBusy,
  onColorImageChosen,
  onTraceByHand,
}) => {
  const [isChoosingFile, setIsChoosingFile] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) onColorImageChosen(file);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Button disabled={isBusy} onClick={() => setIsChoosingFile(true)}>
          I have a region-color image
        </Button>
        <Button variant="secondary" disabled={isBusy} onClick={onTraceByHand}>
          Trace by hand
        </Button>
      </div>
      {isChoosingFile && (
        <label className="block text-sm text-content">
          Region color image (PNG)
          <input
            type="file"
            accept="image/png"
            className="mt-1 block text-sm"
            onChange={handleFileChange}
          />
        </label>
      )}
      {isBusy && <p className="text-sm text-content-muted">Tracing the map…</p>}
      {errorMessage && (
        <p role="alert" className="text-sm text-danger">
          {errorMessage}
        </p>
      )}
    </div>
  );
};
