import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { TermsResult } from "../../../types/scene.types";
import type { SceneOutcomeBannerProps } from "./SceneOutcomeBanner.types";

const RESULT_TEXT: Record<TermsResult, string> = {
  agreed: "The pact is sealed.",
  walked_out: "The ruler walked out of the talks.",
  refused: "The pact was refused.",
};
const FALLBACK_TEXT = "The talks have ended.";

export const SceneOutcomeBanner: React.FC<SceneOutcomeBannerProps> = ({
  outcome,
  onClose,
}) => {
  const text =
    outcome?.kind === "terms_card" ? RESULT_TEXT[outcome.result] : FALLBACK_TEXT;

  return (
    <div role="status" className="flex items-center justify-between gap-2 rounded-md border border-border-strong bg-surface-raised p-3">
      <span className="text-sm font-semibold text-content">{text}</span>
      <Button size="sm" variant="secondary" onClick={onClose}>
        Close
      </Button>
    </div>
  );
};
