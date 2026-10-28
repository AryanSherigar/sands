export interface GenreTileProps {
  genre: string;
  isSelected: boolean;
  isDisabled: boolean;
  onToggle: (genre: string) => void;
  subtitle?: string;
  storyPreview?: string;
  accentColor?: string;
}
