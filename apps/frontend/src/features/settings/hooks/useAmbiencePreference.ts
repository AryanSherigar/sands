import { useEffect, useState } from "react";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";

export const useAmbiencePreference = () => {
  const [volume, setVolumeState] = useState(() => ambientSoundtrack.getVolume());
  const [isMuted, setIsMuted] = useState(() => ambientSoundtrack.getIsMuted());

  useEffect(
    () =>
      ambientSoundtrack.onAudioPreferenceChange((preferences) => {
        setVolumeState(preferences.volume);
        setIsMuted(preferences.isMuted);
      }),
    [],
  );

  const setAmbienceEnabled = (isEnabled: boolean): void => {
    if (isEnabled === isMuted) ambientSoundtrack.toggleMute();
  };

  return {
    volume,
    isAmbienceEnabled: !isMuted,
    setAmbienceEnabled,
    setVolume: (next: number) => ambientSoundtrack.setVolume(next),
  };
};
