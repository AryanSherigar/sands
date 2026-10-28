import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { WelcomePlayback } from "../utils/welcomePlayback";

export function useWelcomeClock(controller: RefObject<WelcomePlayback>, isReady: boolean, onComplete: () => void) {
  const [time, setTime] = useState(-1);
  const [isPaused, setIsPaused] = useState(true);
  const complete = useRef(onComplete); complete.current = onComplete;
  const handlePlay = useCallback(async () => {
    try { await controller.current?.play(); setIsPaused(false); }
    catch (error) { console.warn("Welcome playback requires interaction", error); setIsPaused(true); }
  }, [controller]);
  useEffect(() => {
    if (isReady) void handlePlay();
    else { setTime(-1); setIsPaused(true); }
  }, [isReady, handlePlay]);
  useEffect(() => {
    if (isPaused) return;
    return startClock(controller, setTime, () => complete.current());
  }, [isPaused, controller]);
  const handlePause = () => { controller.current?.pause(); setIsPaused(true); };
  return { time, isPaused, handlePlay, handlePause };
}


function startClock(controller: RefObject<WelcomePlayback>, setTime: (time: number) => void, onComplete: () => void): () => void {
  let frame = 0;
  const update = () => {
    const playback = controller.current;
    if (!playback) return;
    setTime(playback.time);
    if (playback.time >= playback.duration) { onComplete(); return; }
    frame = requestAnimationFrame(update);
  };
  frame = requestAnimationFrame(update);
  return () => cancelAnimationFrame(frame);
}
