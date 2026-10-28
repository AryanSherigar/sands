export interface MeterBarProps {
  label: string;
  value: number;
  clampMin: number;
  clampMax: number;
  tierName?: string | null;
  shouldAnimate: boolean;
}
