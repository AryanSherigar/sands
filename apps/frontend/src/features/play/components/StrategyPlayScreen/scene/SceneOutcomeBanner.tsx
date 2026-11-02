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

const TONE_LABELS: Record<number, string> = {
  0: "Conciliatory",
  1: "Courteous",
  2: "Measured",
  3: "Stern",
  4: "Harsh",
  5: "Outrageous",
};

export const SceneOutcomeBanner: React.FC<SceneOutcomeBannerProps> = ({
  outcome,
  onClose,
}) => {
  const text =
    outcome?.kind === "terms_card" ? RESULT_TEXT[outcome.result] : FALLBACK_TEXT;
  const isTerms = outcome?.kind === "terms_card";
  const toneGrade = isTerms ? outcome.refused_demand?.tone_grade : undefined;
  const isWalkedOut = isTerms && outcome.result === "walked_out";

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-2 rounded-md border border-border-strong bg-surface-raised p-3"
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-content">{text}</span>
        {toneGrade !== undefined && (
          <span
            data-testid="tone-indicator"
            className="rounded bg-surface-tint px-2 py-0.5 text-xs font-semibold text-content-muted"
          >
            Tone: {TONE_LABELS[toneGrade] ?? "Measured"}
          </span>
        )}
        {isWalkedOut && (
          <span
            data-testid="outrage-indicator"
            className="rounded bg-danger/10 px-2 py-0.5 text-xs font-semibold text-danger"
          >
            Outraged
          </span>
        )}
      </div>
      <Button size="sm" variant="secondary" onClick={onClose}>
        Close
      </Button>
    </div>
  );
};
