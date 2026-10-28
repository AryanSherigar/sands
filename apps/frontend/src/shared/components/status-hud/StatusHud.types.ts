import { MeterBarProps } from "./MeterBar.types";
import { TierPipsProps } from "./TierPips.types";

export interface StatusHudProps {
  meters: MeterBarProps[];
  tier?: TierPipsProps | null;
}
