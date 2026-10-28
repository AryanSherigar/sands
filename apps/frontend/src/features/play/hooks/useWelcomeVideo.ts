import { useEffect, type RefObject } from "react";

export function useWelcomeVideo(video: RefObject<HTMLVideoElement>, time: number, isPaused: boolean, picture: string) {
  useEffect(() => {
    const element = video.current;
    if (!element || time < 0) return;
    const offset = time < 1 ? time : time - 1;
    if (Math.abs(element.currentTime - offset) > 0.15) element.currentTime = offset;
    if (isPaused) element.pause();
    else if (element.paused) void element.play().catch(error => console.warn("Welcome picture paused", error));
  }, [video, time, isPaused, picture]);
}
