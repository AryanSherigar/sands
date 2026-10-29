import { EBookAudioControl } from "./EBook/EBookAudioControl";

export interface AudioPlayerProps {
  className?: string;
}

export function AudioPlayer({ className = "" }: AudioPlayerProps) {
  return (
    <div className={`audio-player ${className}`}>
      <EBookAudioControl />
    </div>
  );
}

export { EBookAudioControl };
export default AudioPlayer;
