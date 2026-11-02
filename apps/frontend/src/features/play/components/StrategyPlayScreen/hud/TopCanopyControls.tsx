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
}) => {
  const isAudioMuted = usePlayStore((s) => s.is_audio_muted);
  const setIsAudioMuted = usePlayStore((s) => s.setIsAudioMuted);

  return (
    <div className="pointer-events-auto flex max-w-full flex-wrap items-center justify-end gap-2">
      <ResourceLedgerStrip world={world} onOpenTreasury={onOpenTreasury} />
      <MapModePills activeMode={activeMapMode} onSelectMode={onSelectMapMode} />
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
