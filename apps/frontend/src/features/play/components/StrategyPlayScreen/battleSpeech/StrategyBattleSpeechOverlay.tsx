import { useEffect } from "react";
import { useBattleSpeech } from "../../../hooks/useBattleSpeech";
import { useCrowdAudio } from "../../../hooks/useCrowdAudio";
import { useSkipBattleSpeech } from "../../../hooks/useSkipBattleSpeech";
import { useSubmitSpeechTalk } from "../../../hooks/useSubmitSpeechTalk";
import { describeMoraleChange, TALK_LABELS } from "../../../lib/battleSpeechCopy";
import { useBattleSpeechStore } from "../../../stores/battleSpeech.store";
import { OfficerReport } from "./OfficerReport";
import { SpeechStage } from "./SpeechStage";
import { SpeechTalkInput } from "./SpeechTalkInput";
import type { StrategyBattleSpeechOverlayProps } from "./StrategyBattleSpeechOverlay.types";

const BUTTON_CLASSES =
  "rounded-md bg-[#46606E] px-4 py-2 text-white hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2 disabled:opacity-50";

export function StrategyBattleSpeechOverlay({
  playthroughId,
  battleId,
}: StrategyBattleSpeechOverlayProps) {
  const { speech } = useBattleSpeech(playthroughId, battleId);
  const phase = useBattleSpeechStore((state) => state.phase);
  const lastReaction = useBattleSpeechStore((state) => state.lastReaction);
  const submit = useSubmitSpeechTalk(playthroughId, battleId);
  const skip = useSkipBattleSpeech(playthroughId, battleId);
  const { playReaction } = useCrowdAudio();

  useEffect(() => {
    if (lastReaction) playReaction(lastReaction);
  }, [lastReaction, playReaction]);

  if (!speech) return null;

  const handleStepForward = () => useBattleSpeechStore.getState().beginTalking();
  const handleContinue = () =>
    useBattleSpeechStore.getState().continueAfterReaction(Boolean(submit.result?.is_complete));
  const handleToBattle = () => useBattleSpeechStore.getState().reset();
  const moralePercent = submit.result?.morale_delta_percent ?? speech.outcome?.morale_delta_percent ?? 0;
  const isOpeningOrTalking = phase === "report" || phase === "talking";
  const errorMessage = submit.errorInfo?.message ?? skip.errorInfo?.message;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Address your army"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <section className="max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto rounded-xl bg-[#F7F0DC] p-6 text-[#3A3128] shadow-lg">
        <h2 className="font-serif text-2xl">Address your army</h2>
        <OfficerReport report={speech.officer_report} />
        <SpeechStage mood={speech.mood} reaction={lastReaction} />
        {phase === "report" && (
          <button type="button" onClick={handleStepForward} className={BUTTON_CLASSES}>
            Step forward
          </button>
        )}
        {phase === "talking" && speech.next_talk !== null && (
          <SpeechTalkInput
            playthroughId={playthroughId}
            talkLabel={TALK_LABELS[speech.next_talk]}
            isSubmitting={submit.isPending}
            onSubmit={(text) => submit.submitTalk({ talkIndex: speech.next_talk ?? 1, text })}
          />
        )}
        {phase === "reacting" && (
          <button type="button" onClick={handleContinue} className={BUTTON_CLASSES}>
            Continue
          </button>
        )}
        {phase === "result" && (
          <div className="space-y-3">
            <p className="font-serif text-lg">{describeMoraleChange(moralePercent)}</p>
            <button type="button" onClick={handleToBattle} className={BUTTON_CLASSES}>
              To the battle
            </button>
          </div>
        )}
        {errorMessage && (
          <p role="alert" className="text-sm text-[#A8483E]">
            {errorMessage}
          </p>
        )}
        {isOpeningOrTalking && (
          <button
            type="button"
            disabled={skip.isPending || submit.isPending}
            onClick={() => skip.skip()}
            className="text-sm underline focus-visible:outline focus-visible:outline-2 disabled:opacity-50"
          >
            Skip the speech
          </button>
        )}
      </section>
    </div>
  );
}
