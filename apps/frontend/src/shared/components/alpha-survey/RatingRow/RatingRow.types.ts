export interface RatingRowProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
}
