import React from "react";
import { EBookBottomBar } from "./EBook/EBookBottomBar";
import { EBookHeader } from "./EBook/EBookHeader";
import { ReaderTypographyMenu } from "./EBook/ReaderTypographyMenu";
import { AudioPlayer } from "./AudioPlayer";

export interface ReaderControlsProps {
  isSepia?: boolean;
  className?: string;
  onBack?: () => void;
  onOpenCodex?: () => void;
  onOpenChronicle?: () => void;
  isSpectator?: boolean;
  canAct?: boolean;
  waitingOnLabel?: string | null;
  isEnded?: boolean;
}

export function ReaderControls({
  isSepia = false,
  className = "",
  onBack,
  onOpenCodex,
  onOpenChronicle,
  isSpectator = false,
  canAct = true,
  waitingOnLabel = null,
  isEnded = false,
}: ReaderControlsProps) {
  return (
    <div className={`reader-controls flex items-center justify-between gap-2 ${className}`}>
      <div className="flex items-center gap-2">
        <ReaderTypographyMenu isSepia={isSepia} />
        <AudioPlayer />
      </div>
      {onBack && (
        <EBookHeader
          onBack={onBack}
          onOpenCodex={onOpenCodex}
          onOpenChronicle={onOpenChronicle}
        />
      )}
      <EBookBottomBar
        isSpectator={isSpectator}
        canAct={canAct}
        waitingOnLabel={waitingOnLabel}
        isEnded={isEnded}
      />
    </div>
  );
}

export { EBookBottomBar, EBookHeader, ReaderTypographyMenu };
export default ReaderControls;
