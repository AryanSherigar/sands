import React from "react";
import type { LetterAmbientCanopyProps } from "./StrategyLetterDialog.types";
import type { LetterStage } from "../../../types/letterScene.types";
import { usePlayStore } from "../../../stores/play.store";

function DeskReturnControls({
  stage,
  dispatchNumber,
  onReturnToDesk,
}: {
  stage: LetterStage;
  dispatchNumber: number;
  onReturnToDesk: () => void;
}) {
  return (
    <div className="flex items-center gap-4">
      <button
        type="button"
        onClick={onReturnToDesk}
        aria-label="Return to desk or strategy map (Escape)"
        className="group flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-parchment-panel/90 text-[#2e4856] hover:text-[#182a34] hover:bg-surface-container-high shadow-sm transition-all cursor-pointer border border-[#cfbd94]/50"
      >
        <span className="material-symbols-outlined text-[18px]">west</span>
        <span className="font-serif text-sm font-semibold tracking-wide">
          Return to Desk
        </span>
        <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded bg-surface-container-highest text-on-surface-variant font-bold">
          ESC
        </span>
      </button>
      <div className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-parchment-panel/75 text-on-surface-variant shadow-sm backdrop-blur-sm">
        <span className="material-symbols-outlined text-[18px] text-secondary">
          markunread_mailbox
        </span>
        <span className="text-xs text-on-surface">
          {stage === "reading"
            ? "Unfolded Courier Pouch"
            : "Drafting Courier Missive"}
        </span>
        <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-secondary-fixed text-on-secondary-fixed tracking-tight">
          Dispatch #{dispatchNumber}
        </span>
      </div>
    </div>
  );
}

function DateAndAudioControls({
  dateSolar,
  isMuted,
  onToggleMute,
}: {
  dateSolar: string;
  isMuted: boolean;
  onToggleMute: () => void;
}) {
  return (
    <>
      <div className="hidden lg:flex items-center gap-2 text-on-surface-variant/75 font-display text-body-sm italic tracking-wide">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-meadow-green/60" />
        <span>The Solar at High Cairn • {dateSolar}</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleMute}
          aria-label="Toggle ambient study audio"
          className="w-8 h-8 flex items-center justify-center rounded-full bg-parchment-panel/80 hover:bg-parchment-panel text-on-surface-variant shadow-sm cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">
            {isMuted ? "volume_off" : "volume_up"}
          </span>
        </button>
      </div>
    </>
  );
}

export const LetterAmbientCanopy: React.FC<LetterAmbientCanopyProps> = ({
  stage,
  dispatchNumber,
  dateSolar,
  isMuted: propIsMuted,
  onReturnToDesk,
  onToggleMute,
}) => {
  const storeIsMuted = usePlayStore((s) => s.is_audio_muted);
  const isMuted = storeIsMuted ?? propIsMuted;

  const handleToggleMute = () => {
    const nextMuted = !isMuted;
    if (typeof usePlayStore.getState().setIsAudioMuted === "function") {
      usePlayStore.getState().setIsAudioMuted(nextMuted);
    } else {
      usePlayStore.setState({ is_audio_muted: nextMuted });
    }
    onToggleMute();
  };

  return (
    <header
      aria-label="Study desk controls"
      className="relative z-20 flex items-center justify-between pb-4"
    >
      <DeskReturnControls
        stage={stage}
        dispatchNumber={dispatchNumber}
        onReturnToDesk={onReturnToDesk}
      />
      <DateAndAudioControls
        dateSolar={dateSolar}
        isMuted={isMuted}
        onToggleMute={handleToggleMute}
      />
    </header>
  );
};
