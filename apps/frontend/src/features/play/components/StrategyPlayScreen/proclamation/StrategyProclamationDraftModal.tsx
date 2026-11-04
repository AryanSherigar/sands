import { useState, type FC, type FormEvent } from "react";
import type { ActiveEdictInfo } from "../hud/TopCanopyControls.types";

export interface StrategyProclamationDraftModalProps {
  isOpen: boolean;
  isClassifying?: boolean;
  draftError?: string | null;
  activeEdict?: ActiveEdictInfo | null;
  onSubmitDraft: (text: string, isRescinding: boolean) => void;
  onClose: () => void;
}

export const StrategyProclamationDraftModal: FC<
  StrategyProclamationDraftModalProps
> = ({
  isOpen,
  isClassifying = false,
  draftError,
  activeEdict,
  onSubmitDraft,
  onClose,
}) => {
  const [decreeText, setDecreeText] = useState("");
  const [isRescinding, setIsRescinding] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault();
    if (!decreeText.trim() || isClassifying) return;
    onSubmitDraft(decreeText.trim(), Boolean(activeEdict && isRescinding));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Draft Royal Proclamation"
      className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 p-4 backdrop-blur-sm"
    >
      <div className="relative w-full max-w-xl rounded-xl bg-parchment-panel p-6 font-serif text-on-surface shadow-[0_16px_36px_-4px_rgba(58,49,40,0.16)]">
        <div className="mb-4 flex items-center justify-between border-b border-on-surface/10 pb-3">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[24px] text-secondary">
              history_edu
            </span>
            <h2 className="text-lg font-semibold italic text-on-surface">
              Scribe&apos;s Desk &mdash; Issue Royal Proclamation
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isClassifying}
            aria-label="Close drafting modal"
            className="cursor-pointer text-on-surface-variant transition-colors hover:text-on-surface"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {activeEdict && (
          <div className="mb-4 rounded-lg border border-tertiary/40 bg-tertiary/10 p-3 text-xs leading-relaxed text-tertiary">
            <p className="font-bold mb-1 flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">warning</span>
              Active Edict in Force: {activeEdict.title} ({activeEdict.remainingTurns} turns remaining)
            </p>
            <p className="mb-2">
              The realm may only be governed by one active proclamation at a time. Convening a new decree
              will rescind the previous edict early, inflicting <strong>+10 Fickle Sovereign Unrest</strong> across all provinces.
            </p>
            <label className="flex cursor-pointer items-center gap-2 font-bold text-tertiary">
              <input
                type="checkbox"
                checked={isRescinding}
                onChange={(e) => setIsRescinding(e.target.checked)}
                className="rounded accent-tertiary"
              />
              <span>I acknowledge the unrest penalty and will rescind the previous edict.</span>
            </label>
          </div>
        )}

        {draftError && (
          <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg bg-secondary-container/30 p-3 text-xs italic text-on-surface">
            {draftError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label
              htmlFor="proclamation-input"
              className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-on-surface-variant"
            >
              Decree of the Sovereign (Max 500 characters)
            </label>
            <textarea
              id="proclamation-input"
              value={decreeText}
              onChange={(e) => setDecreeText(e.target.value.slice(0, 500))}
              disabled={isClassifying}
              rows={4}
              placeholder="e.g. Levy 200 silver from the merchant guilds to reinforce our southern garrisons and secure trade routes..."
              className="w-full resize-none rounded-lg bg-[#efe6ce] p-3 text-sm leading-relaxed text-on-surface shadow-[inset_0_2px_4px_rgba(58,49,40,0.09)] focus:outline-none focus:ring-2 focus:ring-primary-container-wilds disabled:opacity-50"
            />
            <div className="mt-1 flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>Costs 2 Royal Mandates upon enactment.</span>
              <span>{decreeText.length} / 500</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-on-surface/10 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isClassifying}
              className="cursor-pointer rounded-lg px-4 py-2 font-serif text-xs font-bold text-on-surface-variant transition-colors hover:text-on-surface"
            >
              Dismiss Scribe
            </button>
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={!decreeText.trim() || isClassifying || Boolean(activeEdict && !isRescinding)}
              className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-gradient-to-b from-[#536e7d] to-[#2e4856] px-5 py-2 font-serif text-xs font-bold text-white shadow-md transition-all hover:brightness-110 active:translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isClassifying ? (
                <>
                  <span className="material-symbols-outlined text-[16px] animate-spin">
                    progress_activity
                  </span>
                  Scribes Reading Law...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">
                    send
                  </span>
                  Convene Council &amp; Read Edict
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
