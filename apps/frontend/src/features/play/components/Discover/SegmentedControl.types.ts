export interface SegmentedControlProps<T extends string> {
  legend: string;
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (next: T | null) => void;
}
