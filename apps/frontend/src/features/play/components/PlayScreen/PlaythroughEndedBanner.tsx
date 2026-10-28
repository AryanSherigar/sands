import { useState } from "react";
import { PostRunSurvey } from "@/shared/components/alpha-survey/PostRunSurvey/PostRunSurvey";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";

interface PlaythroughEndedBannerProps {
  outcomeTag: "win" | "lose";
  outcomeTitle: string;
  outcomeText: string;
  playthroughId: string;
  onBackToLibrary: () => void;
}

export function PlaythroughEndedBanner({
  outcomeTag,
  outcomeTitle,
  outcomeText,
  playthroughId,
  onBackToLibrary,
}: PlaythroughEndedBannerProps) {
  const isAlphaMode = useIsAlphaMode();
  const [isSurveyOpen, setIsSurveyOpen] = useState(false);
  const accentClass =
    outcomeTag === "win"
      ? "border-success/40 text-success"
      : "border-danger/40 text-danger";

  return (
    <div className="fixed inset-x-0 top-0 z-40 flex justify-center px-4 pt-4">
      <div
        role="alert"
        className={`w-full max-w-xl rounded-2xl border bg-surface-overlay/95 backdrop-blur-md shadow-modal p-5 text-center ${accentClass}`}
      >
        <p className="font-mono text-[10px] uppercase tracking-widest opacity-70 mb-1">
          {outcomeTag === "win" ? "Victory" : "Defeat"}
        </p>
        <h2 className="font-serif text-xl font-bold mb-2">{outcomeTitle}</h2>
        <p className="text-sm leading-relaxed text-content-muted mb-4 whitespace-pre-line">
          {outcomeText}
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {isAlphaMode && (
            <button
              type="button"
              onClick={() => setIsSurveyOpen(true)}
              className="min-h-11 px-4 py-2 rounded-xl border border-inherit/30 hover:bg-hover-wash font-mono text-xs transition-colors cursor-pointer"
            >
              Rate this run
            </button>
          )}
          <button
            type="button"
            onClick={onBackToLibrary}
            className="min-h-11 px-4 py-2 rounded-xl border border-inherit/30 hover:bg-hover-wash font-mono text-xs transition-colors cursor-pointer"
          >
            Return to Library
          </button>
        </div>
        <PostRunSurvey
          playthroughId={playthroughId}
          isOpen={isSurveyOpen}
          onClose={() => setIsSurveyOpen(false)}
        />
      </div>
    </div>
  );
}
