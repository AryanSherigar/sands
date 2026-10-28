interface PresetOption {
  id: string;
  name: string;
  url: string;
}

export interface PresetPickerProps {
  label: string;
  options: PresetOption[];
  selectedUrl: string | null;
  onSelect: (url: string) => void;
}
