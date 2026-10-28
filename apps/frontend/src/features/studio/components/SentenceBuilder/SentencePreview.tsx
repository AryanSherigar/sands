import React from "react";
import type { SentencePreviewProps } from "./SentenceBuilder.types";

export const SentencePreview: React.FC<SentencePreviewProps> = ({ text }) => (
  <p aria-live="polite" className="text-meta text-content-muted">
    {text}
  </p>
);
