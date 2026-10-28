import { useEffect, useState, type RefObject } from "react";
import { WelcomePlayback } from "../utils/welcomePlayback";
import { useWelcomeClosing } from "./useWelcomeClosing";
import { WELCOME_VOICE_TIMEOUT } from "../constants/welcomeTape";

export function useWelcomePersonalization(playthroughId: string | null, urls: string[], controller: RefObject<WelcomePlayback>) {
  const [isReady, setIsReady] = useState(false);
  const [isPersonalized, setIsPersonalized] = useState(false);
  const { mutateAsync } = useWelcomeClosing();
  useEffect(() => {
    setIsReady(false); setIsPersonalized(false);
    if (!playthroughId || urls.length === 0) return;
    const playback = controller.current;
    const abort = new AbortController();
    const deadline = window.setTimeout(() => { abort.abort(); setIsReady(true); }, WELCOME_VOICE_TIMEOUT);
    void mutateAsync({ playthroughId, signal: abort.signal })
      .then(content => playback?.setClosing(content, abort.signal))
      .then(isAccepted => { if (!abort.signal.aborted) setIsPersonalized(Boolean(isAccepted)); })
      .catch(error => console.warn("Using generic welcome closing", error))
      .finally(() => { window.clearTimeout(deadline); if (!abort.signal.aborted) setIsReady(true); });
    return () => { abort.abort(); window.clearTimeout(deadline); };
  }, [playthroughId, urls, controller, mutateAsync]);
  return { isReady, isPersonalized };
}
