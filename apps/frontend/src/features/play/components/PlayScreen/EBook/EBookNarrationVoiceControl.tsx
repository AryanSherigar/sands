import { IconVolume, IconVolumeOff } from "@tabler/icons-react";
import { usePlayStore } from "../../../stores/play.store";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { useVoiceOutputPreference } from "@/shared/hooks/useVoiceOutputPreference";

export function EBookNarrationVoiceControl() {
  const theme = usePlayStore((s) => s.ebook_theme);
  const isAlphaMode = useIsAlphaMode();
  const { isVoiceOutputEnabled, setVoiceOutputEnabled, isUpdating } =
    useVoiceOutputPreference();

  const isSepia = theme === "antique-sepia";
  const enabledStyle = isSepia
    ? "border-[#7A6431]/60 bg-[#7A6431]/10 text-[#7A6431]"
    : "border-accent/60 bg-accent/10 text-accent";

  const handleToggle = (): void => {
    setVoiceOutputEnabled(!isVoiceOutputEnabled);
  };

  if (isAlphaMode) return null;

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={isUpdating}
      className={`p-1.5 px-2.5 rounded-xl border font-mono text-xs flex items-center gap-1.5 cursor-pointer transition-colors disabled:opacity-60 ${
        isVoiceOutputEnabled ? enabledStyle : "border-inherit/20 hover:bg-surface-raised"
      }`}
      title={
        isVoiceOutputEnabled
          ? "Voice narration on — click to turn off"
          : "Voice narration off — click to turn on"
      }
      aria-label={
        isVoiceOutputEnabled
          ? "Voice narration on — click to turn off"
          : "Voice narration off — click to turn on"
      }
    >
      <span>
        {isVoiceOutputEnabled ? (
          <IconVolume size={16} stroke={1.5} />
        ) : (
          <IconVolumeOff size={16} stroke={1.5} />
        )}
      </span>
      <span className="hidden sm:inline">Voice</span>
    </button>
  );
}
