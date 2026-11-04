import type { FC } from "react";
import { ResourceLedgerStrip } from "./ResourceLedgerStrip";
import { MapModePills } from "./MapModePills";
import type { TopCanopyControlsProps } from "./TopCanopyControls.types";
import { usePlayStore } from "../../../stores/play.store";

export const TopCanopyControls: FC<TopCanopyControlsProps> = ({
  world,
  activeMapMode,
  onSelectMapMode,
  onOpenTreasury,
  mandatesRemaining,
  activeEdict,
  onIssueProclamation,
}) => {
  const isAudioMuted = usePlayStore((s) => s.is_audio_muted);
  const setIsAudioMuted = usePlayStore((s) => s.setIsAudioMuted);
  const effectiveMandates =
    mandatesRemaining ?? world?.orders_remaining ?? 0;

  return (
    <div className="pointer-events-auto flex max-w-full flex-wrap items-center justify-end gap-2">
      <ResourceLedgerStrip world={world} onOpenTreasury={onOpenTreasury} />
      <MapModePills activeMode={activeMapMode} onSelectMode={onSelectMapMode} />
      {activeEdict && (
        <div
          className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#382F26] text-[#FEEEE0] border border-[#FED16E]/40 shadow-md text-xs font-serif font-medium tracking-wide animate-fade-in"
          title={[
            `Active Royal Edict: ${activeEdict.title} (${activeEdict.remainingTurns} turns remaining)`,
            ...(activeEdict.effects ?? []),
          ].join("\n")}
        >
          <span className="text-[#FED16E] text-sm">✦</span>
          <span>
            Edict: {activeEdict.title} ({activeEdict.remainingTurns}{" "}
            {activeEdict.remainingTurns === 1 ? "turn" : "turns"})
          </span>
        </div>
      )}
      {onIssueProclamation && (
        <button
          type="button"
          onClick={onIssueProclamation}
          disabled={effectiveMandates < 2}
          aria-label="Issue Proclamation (2 Mandates)"
          title={
            effectiveMandates < 2
              ? "Requires 2 Royal Mandates"
              : "Convene the Royal Council to enact a proclamation"
          }
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full border shadow-md backdrop-blur-xl transition-all text-xs font-serif font-semibold tracking-wide ${
            effectiveMandates < 2
              ? "bg-[#F7F0DC]/50 text-[#8C7A6B] border-[#8C7A6B]/20 cursor-not-allowed opacity-60"
              : "bg-[#F7F0DC]/95 hover:bg-[#FAF0E6] text-[#221A12] border-[#3A3128]/20 hover:border-[#FED16E] cursor-pointer"
          }`}
        >
          <span className="material-symbols-outlined text-[16px] text-[#A66326]">
            crown
          </span>
          <span>Issue Proclamation (2 Mandates)</span>
        </button>
      )}
      <button
        type="button"
        onClick={() => setIsAudioMuted(!isAudioMuted)}
        aria-label="Toggle ambient strategy audio"
        className="w-8 h-8 flex items-center justify-center rounded-full bg-[#F7F0DC]/95 hover:bg-[#FAF0E6] text-[#3A3128] border border-[#3A3128]/20 shadow-md backdrop-blur-xl transition cursor-pointer"
      >
        <span className="material-symbols-outlined text-[18px]">
          {isAudioMuted ? "volume_off" : "volume_up"}
        </span>
      </button>
    </div>
  );
};
