import { useEffect, useRef, useState } from "react";
import { WelcomePlayback } from "../utils/welcomePlayback";
import { WELCOME_MEDIA_TIMEOUT } from "../constants/welcomeTape";

export function useWelcomeMedia(attempt: number) {
  const controller = useRef<WelcomePlayback | null>(null);
  const [urls, setUrls] = useState<string[]>([]);
  const [isFailed, setIsFailed] = useState(false);
  useEffect(() => {
    const playback = new WelcomePlayback(); controller.current = playback;
    const abort = new AbortController();
    setIsFailed(false); setUrls([]);
    const deadline = window.setTimeout(() => { abort.abort(); setIsFailed(true); }, WELCOME_MEDIA_TIMEOUT);
    void playback.load(abort.signal).then(result => {
      if (!abort.signal.aborted) setUrls(result);
    }).catch(error => {
      if (abort.signal.aborted) return;
      console.warn("Welcome media unavailable", error); setIsFailed(true);
    }).finally(() => window.clearTimeout(deadline));
    return () => { abort.abort(); window.clearTimeout(deadline); playback.dispose(); };
  }, [attempt]);
  const handleFailure = () => setIsFailed(true);
  return { controller, urls, isFailed, handleFailure };
}
