import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import { useRef, useState } from "react";
import { useWelcomeTape } from "../../hooks/useWelcomeTape";
import { WelcomeTapeControls } from "./WelcomeTapeControls";
import { WelcomeTapePicture } from "./WelcomeTapePicture";
import type { WelcomeTapeOverlayProps } from "./WelcomeTapeOverlay.types";
import "./welcomeTape.css";

export function WelcomeTapeOverlay({ playthroughId, characterName, onComplete }: WelcomeTapeOverlayProps) {
  const dialog = useRef<HTMLDivElement>(null);
  useFocusTrap(dialog, true);
  const tape = useWelcomeTape(playthroughId, onComplete);
  const [hasCaptions, setHasCaptions] = useState(true);
  const isBuffering = useRef(false);
  const handleBuffer = () => { if (!tape.isPaused) { isBuffering.current = true; tape.handlePause(); } };
  const handleReady = () => { if (isBuffering.current) { isBuffering.current = false; void tape.handlePlay(); } };
  const handlePause = () => { isBuffering.current = false; tape.handlePause(); };
  return <div ref={dialog} role="dialog" aria-modal="true" aria-label="Tallis welcome tape" className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black text-stone-200">
    <WelcomeTapePicture urls={tape.urls} time={tape.time} isPaused={tape.isPaused} hasCaptions={hasCaptions}
      characterName={tape.isPersonalized ? characterName : ""} controller={tape.controller.current} onError={tape.handleFailure} onBuffer={handleBuffer} onReady={handleReady} />
    <WelcomeTapeControls isFailed={tape.isFailed} isReady={tape.isClosingReady} isPaused={tape.isPaused}
      isMuted={tape.isMuted} hasCaptions={hasCaptions} onRetry={tape.handleRetry} onPlay={tape.handlePlay}
      onPause={handlePause} onMute={tape.handleMute} onCaptions={() => setHasCaptions(value => !value)} onSkip={onComplete} />
    {tape.time < 0 && !tape.isFailed && <p role="status" className="absolute top-3 font-mono text-xs">ACQUIRING SIGNAL...</p>}
  </div>;
}
