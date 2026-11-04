import { describeReaction } from "../../../lib/battleSpeechCopy";
import {
  EXHAUSTION_FIGURE_CLASSES,
  MORALE_FIGURE_CLASSES,
  REACTION_FIGURE_CLASSES,
  STAGE_FIGURE_COUNT,
} from "../../../lib/speechStageClasses";
import type { SpeechStageProps } from "./SpeechStage.types";

const FIGURE_INDEXES = Array.from({ length: STAGE_FIGURE_COUNT }, (_, index) => index);

export function SpeechStage({ mood, reaction }: SpeechStageProps) {
  const figureClasses = [
    MORALE_FIGURE_CLASSES[mood.morale],
    reaction ? REACTION_FIGURE_CLASSES[reaction.mood] : EXHAUSTION_FIGURE_CLASSES[mood.exhaustion],
  ].join(" ");
  return (
    <div className="space-y-2">
      <div aria-hidden className="flex h-16 items-end justify-center gap-2">
        {FIGURE_INDEXES.map((index) => (
          <span
            key={index}
            className={`h-10 w-3 rounded-t-full bg-[#3A3128] motion-safe:transition-transform ${figureClasses}`}
          />
        ))}
      </div>
      <p role="status" aria-live="polite" className="min-h-6 text-center text-sm italic">
        {reaction ? describeReaction(reaction) : ""}
      </p>
    </div>
  );
}
