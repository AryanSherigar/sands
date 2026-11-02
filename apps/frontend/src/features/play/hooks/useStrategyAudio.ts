import { useEffect, useRef } from "react";
import type { StrategyUIContext } from "@/shared/types/strategy-audio.types";
import type { StrategyWorldSnapshot } from "../types/strategyPlay.types";
import { evaluateStrategyAudio } from "@/shared/lib/audio/strategy/evaluate-strategy-audio";
import { StrategyAudioDirector } from "@/shared/lib/audio/strategy/strategy-audio-director";
import { usePlayStore } from "../stores/play.store";

export interface UseStrategyAudioProps {
  worldState: StrategyWorldSnapshot | null | undefined;
  uiContext: StrategyUIContext;
  seed?: string;
}

export function useStrategyAudio({
  worldState,
  uiContext,
  seed = "sands-strategy",
}: UseStrategyAudioProps): void {
  const directorRef = useRef<StrategyAudioDirector | null>(null);
  const lastTurnRef = useRef<number | undefined>(undefined);
  const isMuted = usePlayStore((s) => s.is_audio_muted);
  const volume = usePlayStore((s) => s.audio_volume);

  useEffect(() => {
    const director = new StrategyAudioDirector({
      isMuted: usePlayStore.getState().is_audio_muted,
      volume: usePlayStore.getState().audio_volume,
    });
    directorRef.current = director;

    const handleUnlock = () => {
      director.unlock();
    };

    window.addEventListener("pointerdown", handleUnlock, { once: true });
    window.addEventListener("keydown", handleUnlock, { once: true });

    return () => {
      window.removeEventListener("pointerdown", handleUnlock);
      window.removeEventListener("keydown", handleUnlock);
      director.destroy();
      directorRef.current = null;
    };
  }, []);

  useEffect(() => {
    directorRef.current?.setIsMuted(isMuted);
  }, [isMuted]);

  useEffect(() => {
    directorRef.current?.setVolume(volume);
  }, [volume]);

  useEffect(() => {
    if (!worldState || !directorRef.current) return;
    const target = evaluateStrategyAudio(
      worldState,
      uiContext,
      seed,
      lastTurnRef.current,
    );
    directorRef.current.applyTarget(target);
    lastTurnRef.current = worldState.turn;
  }, [worldState, uiContext, seed]);
}
