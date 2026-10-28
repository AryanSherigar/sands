export interface BannerPickerProps {
  selectedUrl: string;
  isUploading: boolean;
  onSelect: (url: string) => void;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}
