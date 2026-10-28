export interface ResultSelectProps {
  label: string;
  value: string;
  choices: string[];
  isOptional?: boolean;
  helpText?: string;
  onChange: (value: string) => void;
}
