import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { useToast } from "@/shared/hooks/useToast";
import {
  FEEDBACK_BODY_MAX_CHARS,
  FEEDBACK_CATEGORIES,
} from "../../../constants/alpha-feedback.constants";
import { useSubmitFeedback } from "../../../hooks/useSubmitFeedback";
import { usePlayStore } from "../../../stores/play.store";
import type { FeedbackCategory } from "../../../types/alphaFeedback.types";

const THANKS_MESSAGE = "Thanks, that went to the team.";
const FAILURE_MESSAGE = "Could not send that. Please try again.";

export function FeedbackButton() {
  const isAlphaMode = useIsAlphaMode();
  const playthroughId = usePlayStore((s) => s.playthrough?.playthrough_id);
  const turnCount = usePlayStore((s) => s.playthrough?.turns.length ?? 0);
  const showToast = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [category, setCategory] = useState<FeedbackCategory>("bug");
  const [body, setBody] = useState("");
  const { mutate, isPending } = useSubmitFeedback();

  if (!isAlphaMode || !playthroughId) return null;

  const handleSubmit = (): void => {
    mutate(
      {
        playthrough_id: playthroughId,
        turn_number: turnCount > 0 ? turnCount : null,
        category,
        body: body.trim(),
      },
      {
        onSuccess: () => {
          showToast(THANKS_MESSAGE, "success");
          setBody("");
          setIsOpen(false);
        },
        onError: () => showToast(FAILURE_MESSAGE, "error"),
      },
    );
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="min-h-11 rounded-xl border border-inherit/20 px-2.5 font-mono text-xs hover:bg-surface-raised cursor-pointer transition-colors"
      >
        Feedback
      </button>
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Tell us what happened"
        isSheetOnMobile
      >
        <div className="space-y-4">
          <div role="radiogroup" aria-label="Category" className="flex flex-wrap gap-2">
            {FEEDBACK_CATEGORIES.map((option) => (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={category === option.value}
                onClick={() => setCategory(option.value)}
                className={`min-h-11 rounded-md border px-3 text-sm cursor-pointer ${
                  category === option.value
                    ? "border-primary bg-primary text-primary-contrast"
                    : "border-border-strong bg-surface-raised text-content"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <label className="block space-y-2 text-sm text-content">
            <span>What should we know?</span>
            <textarea
              value={body}
              maxLength={FEEDBACK_BODY_MAX_CHARS}
              onChange={(event) => setBody(event.target.value)}
              className="min-h-28 w-full rounded-md border border-border-strong bg-surface-raised p-3 text-sm text-content"
            />
          </label>
          <div className="flex justify-end">
            <Button onClick={handleSubmit} disabled={isPending || body.trim() === ""}>
              Send
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
