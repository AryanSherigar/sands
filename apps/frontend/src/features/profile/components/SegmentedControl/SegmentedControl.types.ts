interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  ariaLabel: string;
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
}
