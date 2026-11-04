export interface LiveChronicleFeedProps {
  playthroughId?: string;
  chroniclerId?: string | null;
  onJumpToRegion: (regionId: string) => void;
}
