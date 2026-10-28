import { useEffect, useState } from "react";
import { usePlayStore } from "../stores/play.store";
import { useWelcomeMedia } from "./useWelcomeMedia";
import { useWelcomePersonalization } from "./useWelcomePersonalization";
import { useWelcomeClock } from "./useWelcomeClock";

export function useWelcomeTape(playthroughId: string | null, onComplete: () => void) {
  const [attempt, setAttempt] = useState(0);
  const media = useWelcomeMedia(attempt);
  const closing = useWelcomePersonalization(playthroughId, media.urls, media.controller);
  const clock = useWelcomeClock(media.controller, closing.isReady && !media.isFailed, onComplete);
  const isMuted = usePlayStore(state => state.is_audio_muted);
  const volume = usePlayStore(state => state.audio_volume);
  const handleMute = usePlayStore(state => state.toggleAudioMute);
  useEffect(() => {
    media.controller.current?.setMuted(isMuted, volume);
  }, [isMuted, volume, media.controller, media.urls]);
  const handleFailure = () => { clock.handlePause(); media.handleFailure(); };
  const handleRetry = () => { clock.handlePause(); setAttempt(value => value + 1); };
  return { ...media, ...clock, isPersonalized: closing.isPersonalized,
    isClosingReady: closing.isReady && !media.isFailed, isMuted, handleMute, handleRetry, handleFailure };
}
