import type { FC } from "react";
import type { ProclamationMinisterView } from "../../../api/proclamation.api";
import type { CouncilDialogueLine } from "../../../lib/proclamation-lines";
import { ProclamationActionBar } from "./ProclamationActionBar";
import { ProclamationCouncilTable } from "./ProclamationCouncilTable";
import { ProclamationEdictBanner } from "./ProclamationEdictBanner";
import { ProclamationTranscript } from "./ProclamationTranscript";

export interface StrategyProclamationDialogProps {
  isOpen: boolean;
  ministers: ProclamationMinisterView[];
  legalSummary: string;
  domain?: string;
  burden?: string;
  transcript?: CouncilDialogueLine[];
  isStreaming?: boolean;
  isEnacting?: boolean;
  onAddressCouncil?: (speech: string) => void;
  onPronounce: (verdict: "fiat" | "compromise") => void;
  onClose: () => void;
}

export const StrategyProclamationDialog: FC<StrategyProclamationDialogProps> = ({
  isOpen,
  ministers,
  legalSummary,
  domain,
  burden,
  transcript = [],
  isStreaming = false,
  isEnacting = false,
  onAddressCouncil,
  onPronounce,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Royal Proclamation Council"
      className="fixed inset-0 z-50 overflow-y-auto bg-app-bg pb-28 text-on-surface"
    >
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-parchment-panel/85 px-8 shadow-[0_1px_8px_rgba(58,49,40,0.06)] backdrop-blur-md">
        <button
          type="button"
          onClick={onClose}
          disabled={isEnacting}
          className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
            arrow_back
          </span>
          Return to Map
        </button>
        <h1 className="absolute left-1/2 -translate-x-1/2 font-serif text-[18px] font-semibold italic tracking-wide">
          Royal Council: Proclamation
        </h1>
        <span className="w-32" aria-hidden="true" />
      </header>
      <div className="mx-auto flex w-full max-w-[1360px] flex-col gap-6 px-8 pt-4">
        <ProclamationEdictBanner legalSummary={legalSummary} domain={domain} burden={burden} />
        <ProclamationCouncilTable ministers={ministers} />
        <ProclamationTranscript lines={transcript} isStreaming={isStreaming} />
      </div>
      <ProclamationActionBar
        isStreaming={isStreaming}
        isEnacting={isEnacting}
        onAddressCouncil={onAddressCouncil}
        onPronounce={onPronounce}
      />
    </div>
  );
};
