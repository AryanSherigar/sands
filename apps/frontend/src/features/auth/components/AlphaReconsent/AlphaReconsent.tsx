import React from "react";
import {
  LATEST_ALPHA_CONSENT_VERSION,
  getAlphaConsentCopy,
} from "../../constants/alpha-consent";
import { useRecordAlphaConsent } from "../../hooks/useRecordAlphaConsent";
import type { AlphaReconsentProps } from "./AlphaReconsent.types";

const SAVE_FAILED_MESSAGE = "We couldn't save that. Try again.";

export const AlphaReconsent: React.FC<AlphaReconsentProps> = ({ version }) => {
  const { mutate, isPending, isError } = useRecordAlphaConsent();
  const copy = getAlphaConsentCopy(version);

  const handleAccept = (): void => {
    mutate(version ?? LATEST_ALPHA_CONSENT_VERSION);
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-6 py-12 text-content">
      <div className="flex w-full max-w-md flex-col gap-4">
        <h1 className="font-sans text-xl font-semibold">{copy.title}</h1>
        {copy.paragraphs.map((paragraph) => (
          <p key={paragraph} className="text-sm text-content-muted">
            {paragraph}
          </p>
        ))}
        {isError && (
          <p role="alert" className="text-xs text-danger">
            {SAVE_FAILED_MESSAGE}
          </p>
        )}
        <button
          type="button"
          onClick={handleAccept}
          disabled={isPending}
          className="rounded-lg bg-white px-4 py-3 font-sans text-sm font-medium text-black focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-60"
        >
          I accept and continue
        </button>
      </div>
    </main>
  );
};
