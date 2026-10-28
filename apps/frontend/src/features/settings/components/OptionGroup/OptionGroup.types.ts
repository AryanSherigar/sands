interface OptionGroupOption {
  value: string;
  label: string;
}

export interface OptionGroupProps {
  label: string;
  options: OptionGroupOption[];
  value: string;
  onChange: (value: string) => void;
}
