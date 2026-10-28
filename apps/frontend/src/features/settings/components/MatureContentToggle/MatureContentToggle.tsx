import React, { useState } from "react";
import { useMaturePreference } from "@/shared/hooks/useMaturePreference";

const TOGGLE_LABEL = "Show mature content";
const SAVED_MESSAGE = "Saved";

export const MatureContentToggle: React.FC = () => {
  const { isEnabled, isSaving, setEnabled } = useMaturePreference();
  const [isSaved, setIsSaved] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failedTarget, setFailedTarget] = useState<boolean | null>(null);

  const applyChange = async (next: boolean): Promise<void> => {
    setIsSaved(false);
    setErrorMessage(null);
    setFailedTarget(null);
    const result = await setEnabled(next);
    setIsSaved(result.isApplied);
    if (result.errorMessage) {
      setErrorMessage(result.errorMessage);
      setFailedTarget(next);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <label
          htmlFor="show-mature-content"
          className="font-sans text-sm font-medium text-content"
        >
          {TOGGLE_LABEL}
        </label>
        <input
          id="show-mature-content"
          type="checkbox"
          role="switch"
          checked={isEnabled}
          disabled={isSaving}
          onChange={(event) => void applyChange(event.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden="true"
          className="relative h-5 w-9 shrink-0 rounded-full border border-border-subtle bg-surface-sunken transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-3.5 after:w-3.5 after:rounded-full after:bg-content-faint after:transition-transform peer-checked:bg-surface-raised peer-checked:after:translate-x-4 peer-checked:after:bg-content peer-focus-visible:ring-2 peer-focus-visible:ring-primary"
        />
      </div>
      <p className="font-sans text-xs text-content-faint">
        Off by default. When off, stories marked mature are hidden from Discover
        and ask before opening.
      </p>
      <p role="status" aria-live="polite" className="min-h-4 font-sans text-xs">
        {isSaved && <span className="text-success">{SAVED_MESSAGE}</span>}
      </p>
      {errorMessage && (
        <p role="alert" className="font-sans text-xs text-danger">
          {errorMessage}{" "}
          <button
            type="button"
            onClick={() => void applyChange(failedTarget ?? !isEnabled)}
            className="font-semibold underline underline-offset-2"
          >
            Retry
          </button>
        </p>
      )}
    </div>
  );
};
