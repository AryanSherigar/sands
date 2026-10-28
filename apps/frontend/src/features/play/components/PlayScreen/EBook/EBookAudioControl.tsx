import { useState, ChangeEvent } from "react";
import {
  IconSettings,
  IconVolume,
  IconVolume2,
  IconVolumeOff,
} from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { useTensionTier } from "../../../hooks/useTensionTier";

const capitalise = (text: string): string =>
  text.charAt(0).toUpperCase() + text.slice(1);

function renderSpeakerIcon(isMuted: boolean, volume: number) {
  if (isMuted) return <IconVolumeOff size={14} stroke={1.5} />;
  if (volume < 0.4) return <IconVolume size={14} stroke={1.5} />;
  return <IconVolume2 size={14} stroke={1.5} />;
}

export function EBookAudioControl() {
  const [isOpen, setIsOpen] = useState(false);
  const theme = usePlayStore((s) => s.ebook_theme);
  const isMuted = usePlayStore((s) => s.is_audio_muted);
  const volume = usePlayStore((s) => s.audio_volume);
  const activeMood = usePlayStore((s) => s.active_mood);
  const tension = useTensionTier();
  const toggleMute = usePlayStore((s) => s.toggleAudioMute);
  const setVolume = usePlayStore((s) => s.setAudioVolume);

  const isSepia = theme === "antique-sepia";

  const handleToggleMute = () => {
    toggleMute();
  };

  const handleVolumeChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newVol = parseFloat(event.target.value);
    setVolume(newVol);
  };

  const handleTogglePopover = () => {
    setIsOpen((prev) => !prev);
  };

  const labelSource = tension?.value ?? activeMood;
  const moodLabel = labelSource ? capitalise(labelSource) : "Ambient";

  const popoverStyle = isSepia
    ? "bg-[#faf4e8] border-[#d8c7a8] text-[#2c2217]"
    : "bg-surface-overlay border-border-strong text-content shadow-float";

  return (
    <div className="relative flex items-center">
      <div className="flex items-center rounded-xl border border-inherit/20 overflow-hidden font-mono text-xs">
        <button
          type="button"
          onClick={handleToggleMute}
          className="p-1.5 px-2 hover:bg-surface-raised flex items-center gap-1 cursor-pointer transition-colors"
          title={
            isMuted
              ? "Unmute soundtrack"
              : `Soundtrack (${moodLabel}) — Click to mute`
          }
          aria-label={
            isMuted
              ? "Unmute soundtrack"
              : `Soundtrack (${moodLabel}) — Click to mute`
          }
        >
          <span>{renderSpeakerIcon(isMuted, volume)}</span>
          <span className="hidden sm:inline">{moodLabel}</span>
        </button>

        <button
          type="button"
          onClick={handleTogglePopover}
          className="p-1.5 px-1.5 hover:bg-surface-raised border-l border-inherit/20 cursor-pointer text-[10px]"
          title="Adjust soundtrack volume"
          aria-label="Adjust soundtrack volume"
        >
          <IconSettings size={12} stroke={1.5} />
        </button>
      </div>

      {isOpen && (
        <div
          className={`absolute right-0 top-full mt-2 p-3 rounded-xl border shadow-xl flex flex-col gap-2 z-50 w-44 backdrop-blur-md transition-all ${popoverStyle}`}
        >
          <div className="flex justify-between items-center text-[11px] font-mono">
            <span>Soundtrack</span>
            <span>{isMuted ? "Muted" : `${Math.round(volume * 100)}%`}</span>
          </div>

          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-full accent-accent cursor-pointer h-1.5 bg-surface-inset rounded-lg"
          />

          <div className="text-[10px] opacity-70 font-mono flex items-center gap-1 mt-0.5">
            <span>Mood:</span>
            <span className="font-semibold text-content capitalize">
              {activeMood}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
