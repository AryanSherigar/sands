import { useJudgmentDialog } from "../../../hooks/useJudgmentDialog";
import { JudgmentAccusationPlaque } from "./JudgmentAccusationPlaque";
import { JudgmentActionBar } from "./JudgmentActionBar";
import { JudgmentCourtCard } from "./JudgmentCourtCard";
import { JudgmentExitConfirm } from "./JudgmentExitConfirm";
import { JudgmentManuscript } from "./JudgmentManuscript";
import { JudgmentOutcomeReveal } from "./JudgmentOutcomeReveal";
import { JudgmentPanorama } from "./JudgmentPanorama";
import { JudgmentTribunalStrip } from "./JudgmentTribunalStrip";
import { JudgmentVerdictPanel } from "./JudgmentVerdictPanel";
import type { StrategyJudgmentDialogProps } from "./StrategyJudgmentDialog.types";

const SUBJECT_LABELS = { captive: "A captive before the throne", governor: "A governor accused" };

export function StrategyJudgmentDialog({
  isOpen,
  pkg,
  liveText,
  isStreaming,
  failureMessage,
  canRetryOpen = false,
  onRetryOpen,
  onSpeak,
  onPronounce,
  onDismissReveal,
  onClose,
}: StrategyJudgmentDialogProps) {
  const dialog = useJudgmentDialog({
    isActive: isOpen && !pkg.isResolved,
    isBusy: isStreaming,
    spokenExchangesRemaining: pkg.spokenExchangesRemaining,
    onSpeak,
    onPronounce,
    onClose,
  });

  if (!isOpen) return null;

  const canSpeak = pkg.spokenExchangesRemaining > 0;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Judgment of ${pkg.accused.name}`}
      className="fixed inset-0 z-50 overflow-y-auto bg-[#EFE4C8] pb-28 text-[#221A12]"
    >
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-[#F7F0DC]/85 px-4 shadow-sm backdrop-blur-md sm:px-8">
        <button
          type="button"
          onClick={pkg.isResolved ? onDismissReveal : dialog.handleRequestExit}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-[13px] font-semibold uppercase tracking-wider text-[#42474b] hover:bg-[#f0e0d2]/40"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
            arrow_back
          </span>
          Exit
        </button>
        <h1 className="font-serif text-[20px] italic">{`Judgment of ${pkg.accused.name}`}</h1>
        <span className="w-16" aria-hidden="true" />
      </header>
      {dialog.isConfirmingExit ? (
        <JudgmentExitConfirm onStay={dialog.handleStay} onLeave={dialog.handleLeave} />
      ) : null}
      <JudgmentTribunalStrip turn={pkg.turn} summary={pkg.summary} />
      {pkg.isResolved ? (
        <div className="px-4 pt-8 sm:px-8">
          <JudgmentOutcomeReveal lines={pkg.outcomeSummary} onContinue={onDismissReveal} />
        </div>
      ) : (
        <div className="mx-auto grid max-w-[1440px] grid-cols-1 items-start gap-6 px-4 pt-4 sm:px-8 lg:grid-cols-12">
          <div className="flex flex-col gap-4 lg:col-span-8">
            <JudgmentPanorama />
            <div className="grid grid-cols-1 items-stretch gap-2 md:grid-cols-4">
              <JudgmentAccusationPlaque
                charge={pkg.charge}
                subjectLabel={SUBJECT_LABELS[pkg.subjectKind]}
              />
              <section aria-label="The court" className="grid grid-cols-1 gap-2 sm:grid-cols-3 md:col-span-3">
                <JudgmentCourtCard member={pkg.accused} isAccused />
                {pkg.advisors.map((advisor) => (
                  <JudgmentCourtCard
                    key={advisor.participantId}
                    member={advisor}
                    isAccused={false}
                  />
                ))}
              </section>
            </div>
            <JudgmentManuscript pkg={pkg} liveText={liveText} isStreaming={isStreaming} />
            {failureMessage ? (
              <p role="alert" className="rounded bg-[#ffdad6] px-4 py-2 text-[13px] text-[#93000a]">
                {failureMessage}
                {canRetryOpen && onRetryOpen ? (
                  <button type="button" onClick={onRetryOpen} className="ml-3 font-semibold underline">
                    Try again
                  </button>
                ) : null}
              </p>
            ) : null}
            {canSpeak ? null : (
              <p className="text-center text-[12px] italic text-[#42474b]">
                The court has heard enough. Pronounce your judgment.
              </p>
            )}
          </div>
          <div className="lg:sticky lg:top-16 lg:col-span-4">
            <JudgmentVerdictPanel
              selectedVerdict={dialog.selectedVerdict}
              selectedNuance={dialog.selectedNuance}
              isDisabled={isStreaming}
              onSelectVerdict={dialog.handleSelectVerdict}
              onSelectNuance={dialog.handleSelectNuance}
              onPronounce={dialog.handlePronounce}
            />
          </div>
        </div>
      )}
      {pkg.isResolved ? null : (
        <JudgmentActionBar
          draftText={dialog.draftText}
          isBusy={isStreaming}
          canSpeak={canSpeak}
          onDraftChange={dialog.handleDraftChange}
          onSpeak={dialog.handleSpeak}
          onWhisper={dialog.handleDraftChange}
        />
      )}
    </div>
  );
}
