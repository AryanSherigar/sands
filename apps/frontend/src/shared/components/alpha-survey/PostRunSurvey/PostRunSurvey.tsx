import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { RatingRow } from "@/shared/components/alpha-survey/RatingRow/RatingRow";
import { SURVEY_FREE_TEXT_MAX_CHARS } from "@/shared/constants/alpha-survey";
import { useSubmitSurvey } from "@/shared/hooks/useSubmitSurvey";
import type { PostRunAnswers } from "@/shared/types/alphaSurvey.types";
import type { PostRunSurveyProps } from "./PostRunSurvey.types";

const TEXT_AREA_CLASSES =
  "min-h-20 w-full rounded-md border border-border-strong bg-surface-raised p-3 text-sm text-content";

function buildAnswers(
  rating: number,
  scariness: number,
  confusing: string,
  stopped: string,
): PostRunAnswers {
  return {
    rating,
    scariness,
    ...(confusing.trim() && { confusing: confusing.trim() }),
    ...(stopped.trim() && { would_have_stopped: stopped.trim() }),
  };
}

export function PostRunSurvey({
  playthroughId,
  isOpen,
  onClose,
}: PostRunSurveyProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [scariness, setScariness] = useState<number | null>(null);
  const [confusing, setConfusing] = useState("");
  const [stopped, setStopped] = useState("");
  const { mutate, isPending } = useSubmitSurvey();
  const canSubmit = rating !== null && scariness !== null;

  const handleSubmit = (): void => {
    if (rating === null || scariness === null) return;
    mutate(
      {
        kind: "post_run",
        playthrough_id: playthroughId,
        answers: buildAnswers(rating, scariness, confusing, stopped),
      },
      { onSettled: onClose },
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="How was this run?" isSheetOnMobile>
      <div className="space-y-5">
        <RatingRow label="Overall rating (1 low, 5 high)" value={rating} onChange={setRating} />
        <RatingRow label="How scary was it? (1 not at all, 5 very)" value={scariness} onChange={setScariness} />
        <label className="block space-y-2 text-sm text-content">
          <span>Anything confusing?</span>
          <textarea
            value={confusing}
            maxLength={SURVEY_FREE_TEXT_MAX_CHARS}
            onChange={(event) => setConfusing(event.target.value)}
            className={TEXT_AREA_CLASSES}
          />
        </label>
        <label className="block space-y-2 text-sm text-content">
          <span>Where would you have stopped playing?</span>
          <textarea
            value={stopped}
            maxLength={SURVEY_FREE_TEXT_MAX_CHARS}
            onChange={(event) => setStopped(event.target.value)}
            className={TEXT_AREA_CLASSES}
          />
        </label>
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={onClose}>
            Skip
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isPending}>
            Send
          </Button>
        </div>
      </div>
    </Modal>
  );
}
