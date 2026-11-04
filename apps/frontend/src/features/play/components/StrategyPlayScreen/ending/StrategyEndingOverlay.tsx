import { getEndingTierLabel, getEndingTitle } from "./strategyEnding.constants";
import type { StrategyEndingOverlayProps } from "./StrategyEndingOverlay.types";

const SECONDARY_BUTTON_CLASS =
  "rounded-md border border-[#3A3128]/30 px-4 py-2 text-sm font-semibold text-[#3A3128] hover:bg-[#EFE4C8] focus-visible:outline focus-visible:outline-2";

export const StrategyEndingOverlay = ({
  ending,
  onReadLegacy,
  onReturnToScenario,
  onReplay,
}: StrategyEndingOverlayProps) => {
  return (
    <div className="absolute inset-0 z-50 flex items-end justify-center bg-[#3A3128]/50 p-6 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="The reign has ended"
        className="w-full max-w-md rounded-xl border border-[#D2A94A]/60 bg-[#F3EAD3] p-8 text-center shadow-2xl"
      >
        <p className="text-xs font-semibold uppercase tracking-widest text-[#72787C]">
          The reign has ended
        </p>
        <h2 className="mt-3 font-['EB_Garamond',serif] text-4xl font-bold text-[#3A3128]">
          {getEndingTierLabel(ending)}
        </h2>
        <p className="mt-2 font-serif text-lg italic text-[#554A40]">
          {getEndingTitle(ending.ending_id, ending.name)}
        </p>
        <div className="mt-8 flex flex-col gap-3">
          <button
            type="button"
            onClick={onReadLegacy}
            className="rounded-md bg-[#46606E] px-5 py-3 text-white shadow-lg hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2"
          >
            Read the legacy
          </button>
          <div className="flex justify-center gap-3">
            <button type="button" onClick={onReturnToScenario} className={SECONDARY_BUTTON_CLASS}>
              Return to the scenario page
            </button>
            <button type="button" onClick={onReplay} className={SECONDARY_BUTTON_CLASS}>
              Replay
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
