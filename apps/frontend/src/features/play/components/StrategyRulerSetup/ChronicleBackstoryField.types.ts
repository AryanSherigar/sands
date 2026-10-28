export interface ChronicleBackstoryFieldProps {
  backstory: string;
  isRedrafting: boolean;
  onChangeBackstory: (backstory: string) => void;
  onRedraft: () => void;
  chronicleYearLabel?: string;
}
