import { useCallback, useEffect, useRef } from "react";
import { CrowdPlayer } from "../lib/audio/crowdPlayer";
import { usePlayStore } from "../stores/play.store";
import type { CrowdReaction } from "../types/battleSpeech.types";

const readPlayerAudioSettings = () => ({
  isMuted: usePlayStore.getState().is_audio_muted,
  volume: usePlayStore.getState().audio_volume,
});

export function useCrowdAudio() {
  const contextRef = useRef<AudioContext | null>(null);
  const playerRef = useRef<CrowdPlayer | null>(null);

  useEffect(
    () => () => {
      void contextRef.current?.close();
      contextRef.current = null;
      playerRef.current = null;
    },
    [],
  );

  const playReaction = useCallback((reaction: CrowdReaction) => {
    if (!playerRef.current) {
      contextRef.current = new AudioContext();
      playerRef.current = new CrowdPlayer(contextRef.current, readPlayerAudioSettings);
    }
    playerRef.current.play(reaction);
  }, []);

  return { playReaction };
}
